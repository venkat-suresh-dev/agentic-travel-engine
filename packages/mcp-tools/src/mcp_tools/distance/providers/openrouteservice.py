"""OpenRouteService distance matrix provider."""

from __future__ import annotations

import httpx

from mcp_tools.distance.exceptions import (
    DistanceMalformedResponseError,
    DistanceProviderError,
    DistanceProviderTimeoutError,
    DistanceRateLimitError,
)
from mcp_tools.distance.providers.normalize import (
    _same_coordinates,
    build_identical_location_routes,
    parse_openrouteservice_matrix,
)
from mcp_tools.distance.schemas import (
    DistanceMatrixRequest,
    DistanceRoute,
    LocationPoint,
    TravelMode,
)

DEFAULT_OPENROUTESERVICE_BASE_URL = "https://api.openrouteservice.org"
OPENROUTESERVICE_MATRIX_PATH = "/v2/matrix"

_TRAVEL_MODE_TO_PROFILE: dict[TravelMode, str] = {
    TravelMode.DRIVING: "driving-car",
    TravelMode.WALKING: "foot-walking",
}


class OpenRouteServiceDistanceProvider:
    """Compute distance matrices via the OpenRouteService Matrix API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_OPENROUTESERVICE_BASE_URL,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def get_distance_matrix(
        self, request: DistanceMatrixRequest
    ) -> list[DistanceRoute]:
        if _all_pairs_identical(request):
            return build_identical_location_routes(request)

        locations = _unique_locations(request)
        location_index = {
            (round(point.longitude, 6), round(point.latitude, 6)): index
            for index, point in enumerate(locations)
        }
        sources = [
            location_index[(round(point.longitude, 6), round(point.latitude, 6))]
            for point in request.origins
        ]
        destinations = [
            location_index[(round(point.longitude, 6), round(point.latitude, 6))]
            for point in request.destinations
        ]

        profile = _TRAVEL_MODE_TO_PROFILE[request.travel_mode]
        body = {
            "locations": [[point.longitude, point.latitude] for point in locations],
            "sources": sources,
            "destinations": destinations,
            "metrics": ["distance", "duration"],
        }
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}{OPENROUTESERVICE_MATRIX_PATH}/{profile}"

        try:
            if self._client is not None:
                response = self._client.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise DistanceProviderTimeoutError("distance request timed out") from exc
        except httpx.HTTPError as exc:
            raise DistanceProviderError("distance request failed") from exc

        if response.status_code == 429:
            raise DistanceRateLimitError("distance provider rate limited")
        if response.status_code >= 500:
            raise DistanceProviderError("distance provider unavailable")
        if response.status_code >= 400:
            raise DistanceProviderError("distance request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise DistanceMalformedResponseError(
                "distance response was not JSON"
            ) from exc

        routes = parse_openrouteservice_matrix(payload, request=request)
        return _merge_identical_routes(request, routes)


def _unique_locations(request: DistanceMatrixRequest) -> list[LocationPoint]:
    unique: list[LocationPoint] = []
    seen: set[tuple[float, float]] = set()
    for point in [*request.origins, *request.destinations]:
        key = (round(point.longitude, 6), round(point.latitude, 6))
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique


def _all_pairs_identical(request: DistanceMatrixRequest) -> bool:
    return all(
        _same_coordinates(origin, destination)
        for origin in request.origins
        for destination in request.destinations
    )


def _merge_identical_routes(
    request: DistanceMatrixRequest,
    routes: list[DistanceRoute],
) -> list[DistanceRoute]:
    existing = {(route.origin.name, route.destination.name): route for route in routes}
    merged = list(routes)
    for origin in request.origins:
        for destination in request.destinations:
            if not _same_coordinates(origin, destination):
                continue
            key = (origin.name, destination.name)
            if key not in existing:
                merged.append(
                    DistanceRoute(
                        origin=origin,
                        destination=destination,
                        distance_meters=0,
                        duration_seconds=0,
                        travel_mode=request.travel_mode,
                    )
                )
    return merged
