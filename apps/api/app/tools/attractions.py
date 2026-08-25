"""Application boundary for attraction search."""

from __future__ import annotations

from mcp_tools.places.schemas import (
    AttractionSearchRequest,
    AttractionSearchResult,
    PlacesToolMetadata,
)
from mcp_tools.places.service import PlacesService


class AttractionTool:
    """Invoke attraction search through the places service boundary."""

    def __init__(self, places_service: PlacesService) -> None:
        self._places_service = places_service

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> tuple[AttractionSearchResult, PlacesToolMetadata]:
        return self._places_service.search_attractions(request)
