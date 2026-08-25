"""Build distance matrix requests from validated trip requirements."""

from __future__ import annotations

from mcp_tools.distance.exceptions import DistanceValidationError
from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.distance.schemas import DistanceMatrixRequest, TravelMode

from app.domain.trip_request import TripRequest


def build_distance_matrix_request(
    trip_request: TripRequest,
    location_resolver: LocationResolver,
) -> DistanceMatrixRequest:
    """Create a distance tool request from validated trip requirements.

    Uses only validated trip fields already available in graph state:
    departure city as the origin and destination as the destination.
    """
    if not trip_request.departure_city:
        raise DistanceValidationError(
            "departure_city is required for distance matrix lookup"
        )
    if not trip_request.destination:
        raise DistanceValidationError(
            "destination is required for distance matrix lookup"
        )

    origin = location_resolver.resolve(trip_request.departure_city)
    destination = location_resolver.resolve(trip_request.destination)

    return DistanceMatrixRequest(
        origins=[origin],
        destinations=[destination],
        travel_mode=TravelMode.DRIVING,
    )
