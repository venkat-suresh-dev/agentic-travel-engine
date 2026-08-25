"""Normalize SerpApi Google Flights payloads into domain models."""

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


def parse_serpapi_flight_offers(
    payload: object,
    *,
    request: FlightSearchRequest,
) -> list[FlightOffer]:
    if not isinstance(payload, dict):
        raise FlightMalformedResponseError("flight response was not an object")

    offers_raw: list[dict[str, Any]] = []
    for key in ("best_flights", "other_flights"):
        section = payload.get(key)
        if isinstance(section, list):
            for item in section:
                if isinstance(item, dict):
                    offers_raw.append(item)

    if not offers_raw:
        raise FlightNoDataError("flight response contained no offers")

    offers: list[FlightOffer] = []
    for index, item in enumerate(offers_raw):
        offers.append(_parse_offer(item, request=request, index=index))

    if not offers:
        raise FlightNoDataError("flight response contained no usable offers")
    return offers


def _parse_offer(
    raw: dict[str, Any],
    *,
    request: FlightSearchRequest,
    index: int,
) -> FlightOffer:
    flights_raw = raw.get("flights")
    if not isinstance(flights_raw, list) or not flights_raw:
        raise FlightMalformedResponseError("flight option missing flights array")

    segments: list[FlightSegment] = []
    for segment_raw in flights_raw:
        if not isinstance(segment_raw, dict):
            raise FlightMalformedResponseError("segment was not an object")
        segments.append(_parse_segment(segment_raw))

    total_duration = raw.get("total_duration")
    duration = _format_duration_minutes(total_duration)
    stops = max(len(segments) - 1, 0)
    itinerary = FlightItinerary(segments=segments, duration=duration, stops=stops)

    price = raw.get("price")
    if price is None:
        raise FlightMalformedResponseError("flight option missing price")

    carrier = segments[0].carrier
    first_segment = segments[0]
    last_segment = segments[-1]

    return FlightOffer(
        offer_id=f"serpapi-{index}",
        carrier=carrier,
        origin=first_segment.origin,
        destination=last_segment.destination,
        departure_at=first_segment.departure_at,
        arrival_at=last_segment.arrival_at,
        duration=duration,
        stops=stops,
        cabin_class=request.cabin_class,
        price_amount=Decimal(str(price)),
        price_currency=request.currency,
        itineraries=[itinerary],
    )


def _parse_segment(raw: dict[str, Any]) -> FlightSegment:
    departure = raw.get("departure_airport")
    arrival = raw.get("arrival_airport")
    if not isinstance(departure, dict) or not isinstance(arrival, dict):
        raise FlightMalformedResponseError("segment missing airport fields")

    origin = departure.get("id")
    destination = arrival.get("id")
    departure_time = departure.get("time")
    arrival_time = arrival.get("time")
    airline = raw.get("airline")
    flight_number = raw.get("flight_number")
    duration = _format_duration_minutes(raw.get("duration"))

    if not all(
        isinstance(value, str)
        for value in (origin, destination, departure_time, arrival_time, airline)
    ):
        raise FlightMalformedResponseError("segment missing required fields")

    assert isinstance(origin, str)
    assert isinstance(destination, str)
    assert isinstance(departure_time, str)
    assert isinstance(arrival_time, str)
    assert isinstance(airline, str)

    number = str(flight_number) if flight_number is not None else airline

    return FlightSegment(
        origin=origin,
        destination=destination,
        departure_at=_parse_datetime(departure_time),
        arrival_at=_parse_datetime(arrival_time),
        duration=duration,
        flight_number=number,
        carrier=airline,
    )


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")


def _format_duration_minutes(value: object) -> str:
    if isinstance(value, int):
        hours, minutes = divmod(value, 60)
        return f"PT{hours}H{minutes}M"
    if isinstance(value, str) and value.startswith("PT"):
        return value
    return "PT0M"
