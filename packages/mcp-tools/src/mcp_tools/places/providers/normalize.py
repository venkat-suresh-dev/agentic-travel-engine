"""Normalize Google Places API (New) payloads into domain models."""

from __future__ import annotations

from typing import Any

from mcp_tools.places.exceptions import PlacesMalformedResponseError
from mcp_tools.places.schemas import (
    AttractionPlace,
    OpeningHours,
    PriceRange,
    RestaurantPlace,
    RestaurantPriceLevel,
)

_GOOGLE_PRICE_LEVEL_MAP: dict[str, RestaurantPriceLevel] = {
    "PRICE_LEVEL_INEXPENSIVE": RestaurantPriceLevel.INEXPENSIVE,
    "PRICE_LEVEL_MODERATE": RestaurantPriceLevel.MODERATE,
    "PRICE_LEVEL_EXPENSIVE": RestaurantPriceLevel.EXPENSIVE,
    "PRICE_LEVEL_VERY_EXPENSIVE": RestaurantPriceLevel.VERY_EXPENSIVE,
    "INEXPENSIVE": RestaurantPriceLevel.INEXPENSIVE,
    "MODERATE": RestaurantPriceLevel.MODERATE,
    "EXPENSIVE": RestaurantPriceLevel.EXPENSIVE,
    "VERY_EXPENSIVE": RestaurantPriceLevel.VERY_EXPENSIVE,
}


def parse_google_restaurant_places(payload: dict[str, Any]) -> list[RestaurantPlace]:
    """Parse a Google Text Search response into restaurant domain models."""
    places = payload.get("places")
    if places is None:
        return []
    if not isinstance(places, list):
        raise PlacesMalformedResponseError("places field was not an array")

    restaurants: list[RestaurantPlace] = []
    for item in places:
        if not isinstance(item, dict):
            raise PlacesMalformedResponseError("place entry was not an object")
        restaurants.append(_parse_restaurant_place(item))
    return restaurants


def parse_google_attraction_places(payload: dict[str, Any]) -> list[AttractionPlace]:
    """Parse a Google Nearby Search response into attraction domain models."""
    places = payload.get("places")
    if places is None:
        return []
    if not isinstance(places, list):
        raise PlacesMalformedResponseError("places field was not an array")

    attractions: list[AttractionPlace] = []
    for item in places:
        if not isinstance(item, dict):
            raise PlacesMalformedResponseError("place entry was not an object")
        attractions.append(_parse_attraction_place(item))
    return attractions


def _parse_restaurant_place(item: dict[str, Any]) -> RestaurantPlace:
    place_id = _require_string(item.get("id"), field_name="id")
    name = _parse_display_name(item.get("displayName"))
    latitude, longitude = _parse_location(item.get("location"))
    return RestaurantPlace(
        place_id=place_id,
        name=name,
        address=_optional_string(item.get("formattedAddress")),
        latitude=latitude,
        longitude=longitude,
        primary_type=_optional_string(item.get("primaryType")),
        rating=_optional_float(item.get("rating")),
        user_rating_count=_optional_int(item.get("userRatingCount")),
        price_level=_parse_price_level(item.get("priceLevel")),
        price_range=_parse_price_range(item.get("priceRange")),
        opening_hours=_parse_opening_hours(item.get("regularOpeningHours")),
        website=_optional_string(item.get("websiteUri")),
    )


def _parse_attraction_place(item: dict[str, Any]) -> AttractionPlace:
    place_id = _require_string(item.get("id"), field_name="id")
    name = _parse_display_name(item.get("displayName"))
    latitude, longitude = _parse_location(item.get("location"))
    return AttractionPlace(
        place_id=place_id,
        name=name,
        address=_optional_string(item.get("formattedAddress")),
        latitude=latitude,
        longitude=longitude,
        primary_type=_optional_string(item.get("primaryType")),
        rating=_optional_float(item.get("rating")),
        user_rating_count=_optional_int(item.get("userRatingCount")),
        price_level=_parse_price_level(item.get("priceLevel")),
        opening_hours=_parse_opening_hours(item.get("regularOpeningHours")),
        website=_optional_string(item.get("websiteUri")),
    )


def _parse_display_name(value: object) -> str:
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise PlacesMalformedResponseError("displayName was missing")


def _parse_location(value: object) -> tuple[float, float]:
    if not isinstance(value, dict):
        raise PlacesMalformedResponseError("location was missing")
    latitude = _optional_float(value.get("latitude"))
    longitude = _optional_float(value.get("longitude"))
    if latitude is None or longitude is None:
        raise PlacesMalformedResponseError("location coordinates were missing")
    return latitude, longitude


def _parse_price_level(value: object) -> RestaurantPriceLevel | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PlacesMalformedResponseError("priceLevel was not a string")
    mapped = _GOOGLE_PRICE_LEVEL_MAP.get(value)
    if mapped is None:
        return None
    return mapped


def _parse_price_range(value: object) -> PriceRange | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise PlacesMalformedResponseError("priceRange was not an object")
    start = value.get("startPrice")
    end = value.get("endPrice")
    currency = None
    min_units = None
    max_units = None
    if isinstance(start, dict):
        currency = _optional_string(start.get("currencyCode")) or currency
        min_units = _money_units(start.get("units"))
    if isinstance(end, dict):
        currency = _optional_string(end.get("currencyCode")) or currency
        max_units = _money_units(end.get("units"))
    if currency is None and min_units is None and max_units is None:
        return None
    return PriceRange(currency=currency, min_units=min_units, max_units=max_units)


def _parse_opening_hours(value: object) -> OpeningHours | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise PlacesMalformedResponseError("regularOpeningHours was not an object")
    weekday_descriptions = value.get("weekdayDescriptions")
    descriptions: list[str] = []
    if isinstance(weekday_descriptions, list):
        descriptions = [
            item.strip()
            for item in weekday_descriptions
            if isinstance(item, str) and item.strip()
        ]
    open_now = value.get("openNow")
    return OpeningHours(
        open_now=open_now if isinstance(open_now, bool) else None,
        weekday_descriptions=descriptions,
    )


def _money_units(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _require_string(value: object, *, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise PlacesMalformedResponseError(f"{field_name} was missing")


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise PlacesMalformedResponseError("numeric field was invalid") from exc


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise PlacesMalformedResponseError("integer field was invalid") from exc
