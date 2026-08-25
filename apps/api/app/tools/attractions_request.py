"""Build attraction search requests from validated trip requirements."""

from __future__ import annotations

from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.places.exceptions import PlacesValidationError
from mcp_tools.places.schemas import AttractionSearchRequest, SearchLocation

from app.domain.trip_request import TripRequest


def build_attraction_search_request(
    trip_request: TripRequest,
    location_resolver: LocationResolver,
) -> AttractionSearchRequest:
    """Create an attraction search request from validated trip requirements.

    Uses only the validated destination as the search location.
    """
    if not trip_request.destination:
        raise PlacesValidationError("destination is required for attraction search")

    resolved = location_resolver.resolve(trip_request.destination)
    return AttractionSearchRequest(
        location=SearchLocation(
            name=resolved.name,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
        ),
    )
