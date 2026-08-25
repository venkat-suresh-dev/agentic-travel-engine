"""Geocoding provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeocodedLocation:
    name: str
    latitude: float
    longitude: float
    country: str | None = None


class GeocodingProvider(Protocol):
    """Resolve a human-readable location to coordinates."""

    def geocode(self, location: str) -> GeocodedLocation: ...
