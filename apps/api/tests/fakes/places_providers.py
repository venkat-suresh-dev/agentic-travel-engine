"""Fake places providers for API integration tests."""

from __future__ import annotations

from mcp_tools.places.exceptions import (
    PlacesMalformedResponseError,
    PlacesProviderError,
)
from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchRequest,
    RestaurantPlace,
    RestaurantSearchRequest,
)


class FakePlacesProvider:
    def __init__(self, *, should_fail: bool = False, malformed: bool = False) -> None:
        self.should_fail = should_fail
        self.malformed = malformed

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> list[RestaurantPlace]:
        if self.should_fail:
            raise PlacesProviderError("simulated provider failure")
        if self.malformed:
            raise PlacesMalformedResponseError("simulated malformed response")
        return [
            RestaurantPlace(
                place_id="places/ChIJfake-restaurant",
                name="Fake Restaurant",
                address="123 Test Street",
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                primary_type="restaurant",
                rating=4.2,
                user_rating_count=100,
            )
        ]

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> list[AttractionPlace]:
        if self.should_fail:
            raise PlacesProviderError("simulated provider failure")
        if self.malformed:
            raise PlacesMalformedResponseError("simulated malformed response")
        return [
            AttractionPlace(
                place_id="places/ChIJfake-attraction",
                name="Fake Attraction",
                address="456 Test Avenue",
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                primary_type="tourist_attraction",
                rating=4.6,
                user_rating_count=500,
            )
        ]
