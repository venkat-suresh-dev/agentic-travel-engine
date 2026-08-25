"""Airport code resolution protocol."""

from __future__ import annotations

from typing import Protocol


class AirportCodeResolver(Protocol):
    """Resolve a place name or code to an IATA airport/city code."""

    def resolve(self, location: str) -> str: ...
