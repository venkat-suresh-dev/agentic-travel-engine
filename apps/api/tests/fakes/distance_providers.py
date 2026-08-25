"""Fake distance providers for API integration tests."""

from __future__ import annotations

from mcp_tools.distance.exceptions import (
    DistanceMalformedResponseError,
    DistanceProviderError,
    LocationResolutionError,
)
from mcp_tools.distance.schemas import (
    DistanceMatrixRequest,
    DistanceRoute,
    LocationPoint,
)


class FakeLocationResolver:
    _MAPPINGS = {
        "mumbai": LocationPoint(name="Mumbai", latitude=19.076, longitude=72.8777),
        "dubai": LocationPoint(name="Dubai", latitude=25.2048, longitude=55.2708),
        "paris": LocationPoint(name="Paris", latitude=48.8566, longitude=2.3522),
    }

    def resolve(self, location: str) -> LocationPoint:
        normalized = location.strip().lower()
        point = self._MAPPINGS.get(normalized)
        if point is None:
            raise LocationResolutionError(f"location not found: {location}")
        return point


class FakeDistanceProvider:
    def __init__(self, *, should_fail: bool = False, malformed: bool = False) -> None:
        self.should_fail = should_fail
        self.malformed = malformed

    def get_distance_matrix(
        self, request: DistanceMatrixRequest
    ) -> list[DistanceRoute]:
        if self.should_fail:
            raise DistanceProviderError("simulated provider failure")
        if self.malformed:
            raise DistanceMalformedResponseError("simulated malformed response")

        routes: list[DistanceRoute] = []
        for origin in request.origins:
            for destination in request.destinations:
                if round(origin.latitude, 6) == round(
                    destination.latitude, 6
                ) and round(origin.longitude, 6) == round(destination.longitude, 6):
                    routes.append(
                        DistanceRoute(
                            origin=origin,
                            destination=destination,
                            distance_meters=0,
                            duration_seconds=0,
                            travel_mode=request.travel_mode,
                        )
                    )
                    continue
                routes.append(
                    DistanceRoute(
                        origin=origin,
                        destination=destination,
                        distance_meters=2_392_845,
                        duration_seconds=93_642,
                        travel_mode=request.travel_mode,
                    )
                )
        return routes
