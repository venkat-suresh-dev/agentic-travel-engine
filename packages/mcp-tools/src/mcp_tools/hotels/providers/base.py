"""Hotel provider abstractions."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.hotels.schemas import HotelOffer, HotelSearchRequest


class HotelProvider(Protocol):
    """Search hotel offers from an upstream provider."""

    def search_hotels(self, request: HotelSearchRequest) -> list[HotelOffer]: ...
