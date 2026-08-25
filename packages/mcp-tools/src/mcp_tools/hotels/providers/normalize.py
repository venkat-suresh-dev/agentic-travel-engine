"""Normalize Amadeus hotel-offer payloads into domain models."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from mcp_tools.hotels.exceptions import HotelMalformedResponseError, HotelNoDataError
from mcp_tools.hotels.schemas import (
    HotelOffer,
    HotelRoomOption,
    HotelSearchRequest,
    MoneyAmount,
)


def parse_amadeus_hotel_offers(
    payload: object,
    *,
    request: HotelSearchRequest,
    location_name: str,
) -> list[HotelOffer]:
    if not isinstance(payload, dict):
        raise HotelMalformedResponseError("hotel response was not an object")

    data = payload.get("data")
    if not isinstance(data, list):
        raise HotelMalformedResponseError("hotel response missing data array")
    if not data:
        raise HotelNoDataError("hotel response contained no offers")

    hotels: list[HotelOffer] = []
    for item in data:
        if not isinstance(item, dict):
            raise HotelMalformedResponseError("hotel entry was not an object")
        hotel = _parse_hotel_entry(
            item,
            request=request,
            location_name=location_name,
        )
        if hotel is not None:
            hotels.append(hotel)

    if not hotels:
        raise HotelNoDataError("hotel response contained no usable offers")
    return hotels


def _parse_hotel_entry(
    raw: dict[str, Any],
    *,
    request: HotelSearchRequest,
    location_name: str,
) -> HotelOffer | None:
    hotel_raw = raw.get("hotel")
    if not isinstance(hotel_raw, dict):
        raise HotelMalformedResponseError("hotel entry missing hotel object")

    hotel_id = hotel_raw.get("hotelId")
    name = hotel_raw.get("name")
    if not isinstance(hotel_id, str) or not isinstance(name, str):
        raise HotelMalformedResponseError("hotel entry missing identity fields")

    latitude = _optional_float(hotel_raw.get("latitude"))
    longitude = _optional_float(hotel_raw.get("longitude"))
    address = _format_address(hotel_raw)

    offers_raw = raw.get("offers")
    if not isinstance(offers_raw, list) or not offers_raw:
        return None

    room_options: list[HotelRoomOption] = []
    cheapest_nightly: MoneyAmount | None = None
    cheapest_total: MoneyAmount | None = None

    for offer_raw in offers_raw:
        if not isinstance(offer_raw, dict):
            raise HotelMalformedResponseError("hotel offer was not an object")
        room_option = _parse_room_option(offer_raw)
        room_options.append(room_option)
        if (
            cheapest_total is None
            or room_option.total_price.amount < cheapest_total.amount
        ):
            cheapest_total = room_option.total_price
            cheapest_nightly = room_option.nightly_price

    if not room_options:
        return None

    return HotelOffer(
        hotel_id=hotel_id,
        name=name,
        location=location_name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        room_options=room_options,
        nightly_price=cheapest_nightly,
        total_price=cheapest_total,
        check_in=request.check_in,
        check_out=request.check_out,
    )


def _parse_room_option(raw: dict[str, Any]) -> HotelRoomOption:
    room_raw = raw.get("room")
    if not isinstance(room_raw, dict):
        raise HotelMalformedResponseError("hotel offer missing room")

    room_type = _room_type_label(room_raw)
    description = _room_description(room_raw)

    price_raw = raw.get("price")
    if not isinstance(price_raw, dict):
        raise HotelMalformedResponseError("hotel offer missing price")

    currency = price_raw.get("currency")
    total = price_raw.get("total")
    if not isinstance(currency, str) or total is None:
        raise HotelMalformedResponseError("hotel offer missing price fields")

    total_price = MoneyAmount(amount=Decimal(str(total)), currency=currency)
    nightly_price = _extract_nightly_price(price_raw, currency=currency)

    return HotelRoomOption(
        room_type=room_type,
        description=description,
        nightly_price=nightly_price,
        total_price=total_price,
    )


def _extract_nightly_price(
    price_raw: dict[str, Any],
    *,
    currency: str,
) -> MoneyAmount | None:
    variations = price_raw.get("variations")
    if not isinstance(variations, dict):
        return None
    average = variations.get("average")
    if not isinstance(average, dict):
        return None
    base = average.get("base")
    if base is None:
        return None
    return MoneyAmount(amount=Decimal(str(base)), currency=currency)


def _room_type_label(room_raw: dict[str, Any]) -> str:
    estimated = room_raw.get("typeEstimated")
    if isinstance(estimated, dict):
        category = estimated.get("category")
        if isinstance(category, str) and category:
            return category.replace("_", " ").title()
    room_type = room_raw.get("type")
    if isinstance(room_type, str) and room_type:
        return room_type
    return "Standard Room"


def _room_description(room_raw: dict[str, Any]) -> str | None:
    description = room_raw.get("description")
    if isinstance(description, dict):
        text = description.get("text")
        if isinstance(text, str):
            return text
    return None


def _format_address(hotel_raw: dict[str, Any]) -> str | None:
    address_raw = hotel_raw.get("address")
    if isinstance(address_raw, dict):
        lines = address_raw.get("lines")
        city = address_raw.get("cityName")
        country = address_raw.get("countryCode")
        parts: list[str] = []
        if isinstance(lines, list):
            parts.extend(str(line) for line in lines if line)
        if isinstance(city, str):
            parts.append(city)
        if isinstance(country, str):
            parts.append(country)
        if parts:
            return ", ".join(parts)
    city_code = hotel_raw.get("cityCode")
    if isinstance(city_code, str):
        return city_code
    return None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def parse_amadeus_hotel_list(payload: object) -> list[str]:
    """Extract Amadeus hotel IDs from a Hotel List API response."""
    if not isinstance(payload, dict):
        raise HotelMalformedResponseError("hotel list response was not an object")

    data = payload.get("data")
    if not isinstance(data, list):
        raise HotelMalformedResponseError("hotel list response missing data array")
    if not data:
        raise HotelNoDataError("hotel list response contained no hotels")

    hotel_ids: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        hotel_id = item.get("hotelId")
        if isinstance(hotel_id, str) and hotel_id:
            hotel_ids.append(hotel_id)
    if not hotel_ids:
        raise HotelNoDataError("hotel list response contained no usable hotel IDs")
    return hotel_ids
