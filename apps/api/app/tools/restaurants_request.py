"""Build restaurant search requests from validated trip requirements."""

from __future__ import annotations

from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.places.exceptions import PlacesValidationError
from mcp_tools.places.schemas import RestaurantSearchRequest, SearchLocation

from app.domain.trip_request import TripRequest


def build_restaurant_search_request(
    trip_request: TripRequest,
    location_resolver: LocationResolver,
) -> RestaurantSearchRequest:
    """Create a restaurant search request from validated trip requirements.

    Uses only the validated destination as the search location.
    """
    if not trip_request.destination:
        raise PlacesValidationError("destination is required for restaurant search")

    resolved = location_resolver.resolve(trip_request.destination)
    return RestaurantSearchRequest(
        location=SearchLocation(
            name=resolved.name,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
        ),
    )
