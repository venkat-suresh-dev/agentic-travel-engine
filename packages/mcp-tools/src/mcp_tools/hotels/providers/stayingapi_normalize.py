"""Normalize StayingAPI property payloads into domain models."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from mcp_tools.hotels.exceptions import HotelMalformedResponseError, HotelNoDataError
from mcp_tools.hotels.schemas import (
    HotelOffer,
    HotelRoomOption,
    HotelSearchRequest,
    MoneyAmount,
)


def parse_stayingapi_properties(
    payload: object,
    *,
    request: HotelSearchRequest,
) -> list[HotelOffer]:
    if not isinstance(payload, dict):
        raise HotelMalformedResponseError("hotel response was not an object")

    properties = payload.get("properties") or payload.get("data")
    if properties is None:
        properties = payload.get("results")
    if not isinstance(properties, list):
        raise HotelMalformedResponseError("hotel response missing properties array")
    if not properties:
        raise HotelNoDataError("hotel response contained no properties")

    hotels: list[HotelOffer] = []
    for item in properties:
        if not isinstance(item, dict):
            raise HotelMalformedResponseError("hotel property was not an object")
        hotels.append(_parse_property(item, request=request))

    if not hotels:
        raise HotelNoDataError("hotel response contained no usable properties")
    return hotels


def _parse_property(raw: dict[str, Any], *, request: HotelSearchRequest) -> HotelOffer:
    hotel_id = str(raw.get("id") or raw.get("propertyId") or raw.get("hotel_id") or "")
    if not hotel_id:
        raise HotelMalformedResponseError("hotel property missing id")

    name = str(raw.get("name") or raw.get("title") or "Unknown hotel")
    location = _parse_location_name(raw.get("location"), fallback=request.location)
    address = _parse_address(raw)

    latitude, longitude = _parse_coordinates(raw)
    rating = _optional_decimal(
        raw.get("starRating") or raw.get("guestRating") or raw.get("rating")
    )

    nightly_amount, total_amount, currency = _parse_price_fields(raw, request.currency)

    nightly_price = (
        MoneyAmount(amount=nightly_amount, currency=currency)
        if nightly_amount is not None
        else None
    )
    total_price = (
        MoneyAmount(amount=total_amount, currency=currency)
        if total_amount is not None
        else None
    )

    room_option = HotelRoomOption(
        room_type=str(raw.get("propertyType") or raw.get("roomType") or "standard"),
        description=_optional_string(raw.get("roomDescription")),
        nightly_price=nightly_price,
        total_price=total_price or MoneyAmount(amount=Decimal("0"), currency=currency),
    )

    return HotelOffer(
        hotel_id=hotel_id,
        name=name,
        location=location,
        address=address,
        latitude=latitude,
        longitude=longitude,
        rating=rating,
        amenities=_parse_amenities(raw.get("amenities")),
        room_options=[room_option],
        nightly_price=nightly_price,
        total_price=total_price,
        check_in=request.check_in,
        check_out=request.check_out,
    )


def _parse_price_fields(
    raw: dict[str, Any],
    fallback_currency: str,
) -> tuple[Decimal | None, Decimal | None, str]:
    price = raw.get("price")
    if isinstance(price, dict):
        currency = str(price.get("currency") or fallback_currency).upper()
        nightly = _optional_decimal(price.get("nightlyPrice"))
        total = _optional_decimal(price.get("totalPrice"))
        return nightly, total, currency

    currency = str(raw.get("currency") or fallback_currency).upper()
    nightly = _optional_decimal(
        raw.get("pricePerNight") or raw.get("nightlyPrice") or raw.get("price")
    )
    total = _optional_decimal(raw.get("totalPrice") or raw.get("total") or nightly)
    return nightly, total, currency


def _parse_location_name(value: object, *, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("city", "name", "displayName", "address"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return fallback


def _parse_address(raw: dict[str, Any]) -> str | None:
    direct = _optional_string(raw.get("address") or raw.get("fullAddress"))
    if direct:
        return direct
    location = raw.get("location")
    if isinstance(location, dict):
        parts = [
            location.get("address"),
            location.get("city"),
            location.get("country"),
        ]
        joined = ", ".join(
            str(part) for part in parts if isinstance(part, str) and part.strip()
        )
        return joined or None
    return None


def _parse_coordinates(raw: dict[str, Any]) -> tuple[float | None, float | None]:
    latitude = _optional_float(raw.get("latitude") or raw.get("lat"))
    longitude = _optional_float(
        raw.get("longitude") or raw.get("lng") or raw.get("lon")
    )
    location = raw.get("location")
    if isinstance(location, dict):
        latitude = latitude or _optional_float(
            location.get("lat") or location.get("latitude")
        )
        longitude = longitude or _optional_float(
            location.get("lng") or location.get("lon") or location.get("longitude")
        )
        coordinates = location.get("coordinates")
        if isinstance(coordinates, dict):
            latitude = latitude or _optional_float(coordinates.get("lat"))
            longitude = longitude or _optional_float(coordinates.get("lng"))
    return latitude, longitude


def _parse_amenities(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
