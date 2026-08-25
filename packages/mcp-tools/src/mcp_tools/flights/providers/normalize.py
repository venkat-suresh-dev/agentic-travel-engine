"""Normalize Amadeus flight-offer payloads into domain models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp_tools.flights.exceptions import FlightMalformedResponseError, FlightNoDataError
from mcp_tools.flights.schemas import (
    FlightItinerary,
    FlightOffer,
    FlightSearchRequest,
    FlightSegment,
)


def parse_amadeus_flight_offers(
    payload: object,
    *,
    request: FlightSearchRequest,
) -> list[FlightOffer]:
    if not isinstance(payload, dict):
        raise FlightMalformedResponseError("flight response was not an object")

    data = payload.get("data")
    if not isinstance(data, list):
        raise FlightMalformedResponseError("flight response missing data array")
    if not data:
        raise FlightNoDataError("flight response contained no offers")

    offers: list[FlightOffer] = []
    for item in data:
        if not isinstance(item, dict):
            raise FlightMalformedResponseError("flight offer was not an object")
        offers.append(_parse_offer(item, request=request))

    if not offers:
        raise FlightNoDataError("flight response contained no usable offers")
    return offers


def _parse_offer(raw: dict[str, Any], *, request: FlightSearchRequest) -> FlightOffer:
    offer_id = str(raw.get("id", ""))
    if not offer_id:
        raise FlightMalformedResponseError("flight offer missing id")

    price = raw.get("price")
    if not isinstance(price, dict):
        raise FlightMalformedResponseError("flight offer missing price")
    currency = price.get("currency")
    total = price.get("grandTotal") or price.get("total")
    if not isinstance(currency, str) or total is None:
        raise FlightMalformedResponseError("flight offer missing price fields")

    itineraries_raw = raw.get("itineraries")
    if not isinstance(itineraries_raw, list) or not itineraries_raw:
        raise FlightMalformedResponseError("flight offer missing itineraries")

    itineraries: list[FlightItinerary] = []
    all_segments: list[FlightSegment] = []
    for itinerary_raw in itineraries_raw:
        if not isinstance(itinerary_raw, dict):
            raise FlightMalformedResponseError("itinerary was not an object")
        itinerary = _parse_itinerary(itinerary_raw)
        itineraries.append(itinerary)
        all_segments.extend(itinerary.segments)

    if not all_segments:
        raise FlightMalformedResponseError("flight offer contained no segments")

    validating = raw.get("validatingAirlineCodes")
    carrier = (
        str(validating[0])
        if isinstance(validating, list) and validating
        else all_segments[0].carrier
    )

    outbound = itineraries[0]
    first_segment = outbound.segments[0]
    last_segment = outbound.segments[-1]

    return FlightOffer(
        offer_id=offer_id,
        carrier=carrier,
        origin=first_segment.origin,
        destination=last_segment.destination,
        departure_at=first_segment.departure_at,
        arrival_at=last_segment.arrival_at,
        duration=outbound.duration,
        stops=outbound.stops,
        cabin_class=request.cabin_class,
        price_amount=Decimal(str(total)),
        price_currency=currency,
        itineraries=itineraries,
    )


def _parse_itinerary(raw: dict[str, Any]) -> FlightItinerary:
    duration = str(raw.get("duration", ""))
    segments_raw = raw.get("segments")
    if not isinstance(segments_raw, list) or not segments_raw:
        raise FlightMalformedResponseError("itinerary missing segments")

    segments: list[FlightSegment] = []
    for segment_raw in segments_raw:
        if not isinstance(segment_raw, dict):
            raise FlightMalformedResponseError("segment was not an object")
        segments.append(_parse_segment(segment_raw))

    stops = max(len(segments) - 1, 0)
    return FlightItinerary(segments=segments, duration=duration, stops=stops)


def _parse_segment(raw: dict[str, Any]) -> FlightSegment:
    departure = raw.get("departure")
    arrival = raw.get("arrival")
    if not isinstance(departure, dict) or not isinstance(arrival, dict):
        raise FlightMalformedResponseError("segment missing departure or arrival")

    origin = departure.get("iataCode")
    destination = arrival.get("iataCode")
    departure_at = departure.get("at")
    arrival_at = arrival.get("at")
    carrier = raw.get("carrierCode")
    number = raw.get("number")
    duration = str(raw.get("duration", ""))

    if not all(
        isinstance(value, str)
        for value in (origin, destination, departure_at, arrival_at, carrier, number)
    ):
        raise FlightMalformedResponseError("segment missing required fields")

    assert isinstance(origin, str)
    assert isinstance(destination, str)
    assert isinstance(departure_at, str)
    assert isinstance(arrival_at, str)
    assert isinstance(carrier, str)
    assert isinstance(number, str)

    return FlightSegment(
        origin=origin,
        destination=destination,
        departure_at=datetime.fromisoformat(departure_at),
        arrival_at=datetime.fromisoformat(arrival_at),
        duration=duration,
        flight_number=f"{carrier}{number}",
        carrier=carrier,
    )
