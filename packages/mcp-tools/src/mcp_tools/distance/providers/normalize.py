"""Normalize OpenRouteService matrix payloads into domain models."""

from __future__ import annotations

from typing import Any

from mcp_tools.distance.exceptions import (
    DistanceMalformedResponseError,
    DistanceNoDataError,
)
from mcp_tools.distance.schemas import (
    DistanceMatrixRequest,
    DistanceRoute,
    LocationPoint,
    TravelMode,
)


def parse_openrouteservice_matrix(
    payload: object,
    *,
    request: DistanceMatrixRequest,
) -> list[DistanceRoute]:
    if not isinstance(payload, dict):
        raise DistanceMalformedResponseError("distance response was not an object")

    distances = payload.get("distances")
    durations = payload.get("durations")
    if not isinstance(distances, list) or not isinstance(durations, list):
        raise DistanceMalformedResponseError("distance response missing matrix arrays")

    routes: list[DistanceRoute] = []
    for origin_index, origin in enumerate(request.origins):
        distance_row = _matrix_row(distances, origin_index)
        duration_row = _matrix_row(durations, origin_index)
        for destination_index, destination in enumerate(request.destinations):
            distance_value = distance_row[destination_index]
            duration_value = duration_row[destination_index]
            route = _parse_route_cell(
                origin=origin,
                destination=destination,
                distance_value=distance_value,
                duration_value=duration_value,
                travel_mode=request.travel_mode,
            )
            if route is not None:
                routes.append(route)

    if not routes:
        raise DistanceNoDataError("distance response contained no usable routes")
    return routes


def build_identical_location_routes(
    request: DistanceMatrixRequest,
) -> list[DistanceRoute]:
    """Return zero-distance routes for identical origin/destination coordinate pairs."""
    routes: list[DistanceRoute] = []
    for origin in request.origins:
        for destination in request.destinations:
            if _same_coordinates(origin, destination):
                routes.append(
                    DistanceRoute(
                        origin=origin,
                        destination=destination,
                        distance_meters=0,
                        duration_seconds=0,
                        travel_mode=request.travel_mode,
                    )
                )
    return routes


def _matrix_row(matrix: list[Any], index: int) -> list[Any]:
    if index >= len(matrix):
        raise DistanceMalformedResponseError("distance matrix row missing")
    row = matrix[index]
    if not isinstance(row, list):
        raise DistanceMalformedResponseError("distance matrix row was not an array")
    return row


def _parse_route_cell(
    *,
    origin: LocationPoint,
    destination: LocationPoint,
    distance_value: object,
    duration_value: object,
    travel_mode: TravelMode,
) -> DistanceRoute | None:
    if distance_value is None or duration_value is None:
        return None
    try:
        distance_meters = int(round(float(str(distance_value))))
        duration_seconds = int(round(float(str(duration_value))))
    except (TypeError, ValueError) as exc:
        raise DistanceMalformedResponseError(
            "distance matrix cell was not numeric"
        ) from exc
    return DistanceRoute(
        origin=origin,
        destination=destination,
        distance_meters=max(distance_meters, 0),
        duration_seconds=max(duration_seconds, 0),
        travel_mode=travel_mode,
    )


def _same_coordinates(origin: LocationPoint, destination: LocationPoint) -> bool:
    return round(origin.latitude, 6) == round(destination.latitude, 6) and round(
        origin.longitude, 6
    ) == round(destination.longitude, 6)
