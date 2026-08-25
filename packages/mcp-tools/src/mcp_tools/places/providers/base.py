"""Places provider abstractions."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchRequest,
    RestaurantPlace,
    RestaurantSearchRequest,
)


class PlacesProvider(Protocol):
    """Search restaurants and attractions from an upstream provider."""

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> list[RestaurantPlace]: ...

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> list[AttractionPlace]: ...
