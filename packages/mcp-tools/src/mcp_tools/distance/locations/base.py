"""Location resolution for distance matrix requests."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.distance.schemas import LocationPoint


class LocationResolver(Protocol):
    """Resolve human-readable locations to normalized coordinates."""

    def resolve(self, location: str) -> LocationPoint: ...
