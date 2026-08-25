"""Hotel tool application boundary."""

from __future__ import annotations

from mcp_tools.hotels.schemas import (
    HotelSearchRequest,
    HotelSearchResult,
    HotelToolMetadata,
)
from mcp_tools.hotels.service import HotelService


class HotelTool:
    """Invoke the MCP-backed hotel search capability from the application layer."""

    def __init__(self, hotel_service: HotelService | None = None) -> None:
        if hotel_service is None:
            msg = "hotel_service is required"
            raise ValueError(msg)
        self._hotel_service = hotel_service

    @property
    def hotel_service(self) -> HotelService:
        return self._hotel_service

    def search_hotels(
        self,
        request: HotelSearchRequest,
    ) -> tuple[HotelSearchResult, HotelToolMetadata]:
        """Fetch normalized hotel search results with provenance metadata."""
        result, metadata = self._hotel_service.search_hotels(request)
        return result, metadata
