"""Build attraction search requests from validated trip requirements."""

from __future__ import annotations

from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.places.exceptions import PlacesValidationError
from mcp_tools.places.schemas import (
    MAX_ALLOWED_RESULTS,
    AttractionCategory,
    AttractionSearchRequest,
    SearchLocation,
)

from app.domain.trip_request import TripRequest


def build_attraction_search_request(
    trip_request: TripRequest,
    location_resolver: LocationResolver,
) -> AttractionSearchRequest:
    """Create an attraction search request scaled to trip duration.

    Retrieves a deeper candidate pool across multiple categories so the
    composer can build varied multi-day itineraries without repetition.
    """
    if not trip_request.destination:
        raise PlacesValidationError("destination is required for attraction search")

    resolved = location_resolver.resolve(trip_request.destination)
    duration = trip_request.duration_days or 5
    travelers = trip_request.travelers or 2

    max_results = min(
        MAX_ALLOWED_RESULTS,
        max(12, duration * 4 + travelers),
    )
    radius_meters = min(50_000, max(8_000, 6_000 + duration * 2_000))

    categories = [
        AttractionCategory.TOURIST_ATTRACTION,
        AttractionCategory.MUSEUM,
        AttractionCategory.PARK,
        AttractionCategory.HISTORICAL_LANDMARK,
        AttractionCategory.ART_GALLERY,
    ]

    return AttractionSearchRequest(
        location=SearchLocation(
            name=resolved.name,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
        ),
        max_results=max_results,
        radius_meters=radius_meters,
        categories=categories,
    )
