"""Application boundary for restaurant search."""

from __future__ import annotations

from mcp_tools.places.schemas import (
    PlacesToolMetadata,
    RestaurantSearchRequest,
    RestaurantSearchResult,
)
from mcp_tools.places.service import PlacesService


class RestaurantTool:
    """Invoke restaurant search through the places service boundary."""

    def __init__(self, places_service: PlacesService) -> None:
        self._places_service = places_service

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> tuple[RestaurantSearchResult, PlacesToolMetadata]:
        return self._places_service.search_restaurants(request)
