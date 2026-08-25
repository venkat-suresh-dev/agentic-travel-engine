"""Geocoding-backed location resolver for distance requests."""

from __future__ import annotations

from mcp_tools.distance.exceptions import LocationResolutionError
from mcp_tools.distance.schemas import LocationPoint
from mcp_tools.weather.exceptions import GeocodingError
from mcp_tools.weather.geocoding.base import GeocodingProvider


class GeocodingLocationResolver:
    """Resolve place names using an injected geocoding provider."""

    def __init__(self, geocoding_provider: GeocodingProvider) -> None:
        self._geocoding_provider = geocoding_provider

    def resolve(self, location: str) -> LocationPoint:
        try:
            geocoded = self._geocoding_provider.geocode(location)
        except GeocodingError as exc:
            raise LocationResolutionError(str(exc)) from exc
        return LocationPoint(
            name=geocoded.name,
            latitude=geocoded.latitude,
            longitude=geocoded.longitude,
        )
