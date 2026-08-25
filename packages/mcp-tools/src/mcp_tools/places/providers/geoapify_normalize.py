"""Normalize Geoapify Places payloads into domain models."""

from __future__ import annotations

from typing import Any

from mcp_tools.places.exceptions import PlacesMalformedResponseError
from mcp_tools.places.schemas import (
    AttractionPlace,
    OpeningHours,
    RestaurantPlace,
    RestaurantPriceLevel,
)

_GEOAPIFY_PRICE_LEVEL_MAP: dict[str, RestaurantPriceLevel] = {
    "low": RestaurantPriceLevel.INEXPENSIVE,
    "medium": RestaurantPriceLevel.MODERATE,
    "high": RestaurantPriceLevel.EXPENSIVE,
    "very_high": RestaurantPriceLevel.VERY_EXPENSIVE,
}


def parse_geoapify_restaurant_places(payload: dict[str, Any]) -> list[RestaurantPlace]:
    features = _extract_features(payload)
    restaurants: list[RestaurantPlace] = []
    for feature in features:
        restaurants.append(_parse_restaurant_feature(feature))
    return restaurants


def parse_geoapify_attraction_places(payload: dict[str, Any]) -> list[AttractionPlace]:
    features = _extract_features(payload)
    attractions: list[AttractionPlace] = []
    for feature in features:
        parsed = _parse_attraction_feature(feature)
        if parsed is not None:
            attractions.append(parsed)
    return attractions


def _extract_features(payload: dict[str, Any]) -> list[dict[str, Any]]:
    features = payload.get("features")
    if features is None:
        return []
    if not isinstance(features, list):
        raise PlacesMalformedResponseError("features field was not an array")
    return [item for item in features if isinstance(item, dict)]


def _parse_restaurant_feature(feature: dict[str, Any]) -> RestaurantPlace:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise PlacesMalformedResponseError("feature missing properties")

    place_id = _resolve_place_id(properties)
    name = _require_string(properties.get("name"), field_name="name")
    latitude, longitude = _parse_coordinates(feature, properties)

    return RestaurantPlace(
        place_id=place_id,
        name=name,
        address=_build_address(properties),
        latitude=latitude,
        longitude=longitude,
        primary_type=_optional_string(
            properties.get("categories", [None])[0]
            if isinstance(properties.get("categories"), list)
            else properties.get("category")
        ),
        rating=_optional_float(properties.get("rating")),
        user_rating_count=_optional_int(properties.get("rating_count")),
        price_level=_parse_price_level(properties.get("price")),
        opening_hours=_parse_opening_hours(properties.get("opening_hours")),
        website=_optional_string(properties.get("website")),
    )


def _parse_attraction_feature(feature: dict[str, Any]) -> AttractionPlace | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise PlacesMalformedResponseError("feature missing properties")

    name = _resolve_place_name(properties)
    if name is None:
        return None

    place_id = _resolve_place_id(properties)
    latitude, longitude = _parse_coordinates(feature, properties)

    return AttractionPlace(
        place_id=place_id,
        name=name,
        address=_build_address(properties),
        latitude=latitude,
        longitude=longitude,
        primary_type=_optional_string(
            properties.get("categories", [None])[0]
            if isinstance(properties.get("categories"), list)
            else properties.get("category")
        ),
        rating=_optional_float(properties.get("rating")),
        user_rating_count=_optional_int(properties.get("rating_count")),
        price_level=_parse_price_level(properties.get("price")),
        opening_hours=_parse_opening_hours(properties.get("opening_hours")),
        website=_optional_string(properties.get("website")),
    )


def _parse_coordinates(
    feature: dict[str, Any],
    properties: dict[str, Any],
) -> tuple[float, float]:
    geometry = feature.get("geometry")
    if isinstance(geometry, dict):
        coordinates = geometry.get("coordinates")
        if isinstance(coordinates, list) and len(coordinates) >= 2:
            return float(coordinates[1]), float(coordinates[0])

    lat = properties.get("lat")
    lon = properties.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon)

    raise PlacesMalformedResponseError("feature missing coordinates")


def _build_address(properties: dict[str, Any]) -> str | None:
    formatted = properties.get("formatted")
    if isinstance(formatted, str) and formatted.strip():
        return formatted.strip()
    parts = [
        properties.get("address_line1"),
        properties.get("address_line2"),
        properties.get("city"),
        properties.get("country"),
    ]
    joined = ", ".join(
        str(part) for part in parts if isinstance(part, str) and part.strip()
    )
    return joined or None


def _parse_opening_hours(value: object) -> OpeningHours | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return OpeningHours(weekday_descriptions=[value.strip()])


def _parse_price_level(value: object) -> RestaurantPriceLevel | None:
    if isinstance(value, str):
        return _GEOAPIFY_PRICE_LEVEL_MAP.get(value.lower())
    return None


def _resolve_place_name(properties: dict[str, Any]) -> str | None:
    for key in ("name", "address_line1", "formatted", "street"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_place_id(properties: dict[str, Any]) -> str:
    direct = properties.get("place_id")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    datasource = properties.get("datasource")
    if isinstance(datasource, dict):
        raw = datasource.get("raw")
        if isinstance(raw, dict):
            raw_id = raw.get("id")
            if isinstance(raw_id, str) and raw_id.strip():
                return raw_id.strip()
    name = properties.get("name")
    lat = properties.get("lat")
    lon = properties.get("lon")
    if (
        isinstance(name, str)
        and isinstance(lat, (int, float))
        and isinstance(lon, (int, float))
    ):
        return f"geoapify:{name}:{lat}:{lon}"
    raise PlacesMalformedResponseError("place missing place_id")


def _require_string(value: object, *, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise PlacesMalformedResponseError(f"place missing {field_name}")


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
