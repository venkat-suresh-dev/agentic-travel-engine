"""City code resolution for hotel search."""

from __future__ import annotations

from typing import Protocol


class CityCodeResolver(Protocol):
    """Resolve human-readable locations to IATA city codes."""

    def resolve(self, location: str) -> str: ...
