"""Distance MCP tool tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mcp_tools.distance.cache import DistanceCache
from mcp_tools.distance.exceptions import (
    DistanceProviderError,
    DistanceProviderTimeoutError,
)
from mcp_tools.distance.mcp_server import create_distance_mcp_server
from mcp_tools.distance.providers.normalize import parse_openrouteservice_matrix
from mcp_tools.distance.schemas import (
    DistanceDataStatus,
    DistanceMatrixRequest,
    LocationPoint,
    TravelMode,
)
from mcp_tools.distance.service import DistanceService
from tests.fakes import FakeDistanceProvider, FakeLocationResolver

FIXTURES_DIR = Path(__file__).parent / "fixtures"

MUMBAI = LocationPoint(name="Mumbai", latitude=19.076, longitude=72.8777)
DUBAI = LocationPoint(name="Dubai", latitude=25.2048, longitude=55.2708)
PARIS = LocationPoint(name="Paris", latitude=48.8566, longitude=2.3522)


@pytest.fixture
def one_to_one_request() -> DistanceMatrixRequest:
    return DistanceMatrixRequest(
        origins=[MUMBAI],
        destinations=[DUBAI],
        travel_mode=TravelMode.DRIVING,
    )


@pytest.fixture
def matrix_request() -> DistanceMatrixRequest:
    return DistanceMatrixRequest(
        origins=[MUMBAI, DUBAI],
        destinations=[DUBAI, PARIS],
        travel_mode=TravelMode.DRIVING,
    )


def test_one_origin_one_destination_validation() -> None:
    request = DistanceMatrixRequest(
        origins=[MUMBAI],
        destinations=[DUBAI],
        travel_mode=TravelMode.DRIVING,
    )
    assert len(request.origins) == 1


def test_multiple_origins_destinations_validation() -> None:
    request = DistanceMatrixRequest(
        origins=[MUMBAI, DUBAI],
        destinations=[DUBAI, PARIS],
        travel_mode=TravelMode.DRIVING,
    )
    assert len(request.origins) == 2
    assert len(request.destinations) == 2


def test_valid_travel_mode() -> None:
    request = DistanceMatrixRequest(
        origins=[MUMBAI],
        destinations=[DUBAI],
        travel_mode=TravelMode.WALKING,
    )
    assert request.travel_mode is TravelMode.WALKING


def test_empty_origins_rejected() -> None:
    with pytest.raises(ValueError):
        DistanceMatrixRequest(
            origins=[],
            destinations=[DUBAI],
            travel_mode=TravelMode.DRIVING,
        )


def test_empty_destinations_rejected() -> None:
    with pytest.raises(ValueError):
        DistanceMatrixRequest(
            origins=[MUMBAI],
            destinations=[],
            travel_mode=TravelMode.DRIVING,
        )


def test_malformed_coordinates_rejected() -> None:
    with pytest.raises(ValueError):
        LocationPoint(name="Invalid", latitude=120.0, longitude=0.0)


def test_identical_origin_destination_returns_zero_route() -> None:
    service = DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=DistanceCache(),
    )
    request = DistanceMatrixRequest(
        origins=[MUMBAI],
        destinations=[MUMBAI],
        travel_mode=TravelMode.DRIVING,
    )

    result, _metadata = service.get_distance_matrix(request)

    assert result.routes[0].distance_meters == 0
    assert result.routes[0].duration_seconds == 0


def test_live_distance_response_has_provenance(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    service = DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=DistanceCache(),
    )

    result, metadata = service.get_distance_matrix(one_to_one_request)

    assert result.data_status is DistanceDataStatus.LIVE
    assert result.source == "openrouteservice"
    assert result.routes
    assert result.routes[0].distance_meters == 2_392_845
    assert result.routes[0].duration_seconds == 93_642
    assert result.routes[0].travel_mode is TravelMode.DRIVING
    assert metadata.tool_name == "get_distance_matrix"
    assert metadata.cache_status == "miss"


def test_openrouteservice_fixture_normalization() -> None:
    request = DistanceMatrixRequest(
        origins=[MUMBAI, DUBAI],
        destinations=[MUMBAI, DUBAI],
        travel_mode=TravelMode.DRIVING,
    )
    payload = json.loads((FIXTURES_DIR / "openrouteservice_matrix.json").read_text())
    routes = parse_openrouteservice_matrix(payload, request=request)

    assert len(routes) == 4
    mumbai_to_dubai = next(
        route
        for route in routes
        if route.origin.name == "Mumbai" and route.destination.name == "Dubai"
    )
    assert mumbai_to_dubai.distance_meters == 2_392_845
    assert mumbai_to_dubai.duration_seconds == 93_642


def test_malformed_provider_response_is_unavailable(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    service = DistanceService(
        distance_provider=FakeDistanceProvider(malformed=True),
        cache=DistanceCache(),
    )

    result, _metadata = service.get_distance_matrix(one_to_one_request)

    assert result.data_status is DistanceDataStatus.UNAVAILABLE


def test_cache_hit_returns_cached_status(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    cache = DistanceCache(ttl_seconds=600)
    service = DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=cache,
    )
    service.get_distance_matrix(one_to_one_request)

    failing_service = DistanceService(
        distance_provider=FakeDistanceProvider(should_fail=True),
        cache=cache,
    )
    result, metadata = failing_service.get_distance_matrix(one_to_one_request)

    assert result.data_status is DistanceDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_provider_failure_without_cache_is_unavailable(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    service = DistanceService(
        distance_provider=FakeDistanceProvider(should_fail=True),
        cache=DistanceCache(),
    )

    result, _metadata = service.get_distance_matrix(one_to_one_request)

    assert result.data_status is DistanceDataStatus.UNAVAILABLE
    assert result.routes == []


def test_provider_retries_once_before_failure(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    attempts = {"count": 0}

    class FlakyDistanceProvider(FakeDistanceProvider):
        def get_distance_matrix(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise DistanceProviderError("temporary failure")
            return super().get_distance_matrix(request)

    service = DistanceService(
        distance_provider=FlakyDistanceProvider(),
        cache=DistanceCache(),
    )

    result, _metadata = service.get_distance_matrix(one_to_one_request)

    assert attempts["count"] == 2
    assert result.data_status is DistanceDataStatus.LIVE


def test_provider_timeout_retries_then_unavailable(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    attempts = {"count": 0}

    class TimeoutDistanceProvider(FakeDistanceProvider):
        def get_distance_matrix(self, request):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            raise DistanceProviderTimeoutError("simulated timeout")

    service = DistanceService(
        distance_provider=TimeoutDistanceProvider(),
        cache=DistanceCache(),
    )

    result, _metadata = service.get_distance_matrix(one_to_one_request)

    assert attempts["count"] == 2
    assert result.data_status is DistanceDataStatus.UNAVAILABLE


def test_cache_expiry_allows_new_live_fetch(
    one_to_one_request: DistanceMatrixRequest,
) -> None:
    cache = DistanceCache(ttl_seconds=1)
    service = DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=cache,
    )
    first, _ = service.get_distance_matrix(one_to_one_request)

    key = DistanceCache.cache_key(one_to_one_request)
    entry = cache.get(key)
    assert entry is not None
    cache._entries[key] = type(entry)(
        result=entry.result,
        stored_at=datetime.now(UTC) - timedelta(seconds=2),
    )

    second, metadata = service.get_distance_matrix(one_to_one_request)

    assert second.data_status is DistanceDataStatus.LIVE
    assert second.retrieved_at >= first.retrieved_at
    assert metadata.cache_status == "miss"


def test_normalized_cache_key(one_to_one_request: DistanceMatrixRequest) -> None:
    key = DistanceCache.cache_key(one_to_one_request)
    assert key.endswith(">>driving")


def test_different_travel_modes_produce_different_cache_keys() -> None:
    driving = DistanceMatrixRequest(
        origins=[MUMBAI],
        destinations=[DUBAI],
        travel_mode=TravelMode.DRIVING,
    )
    walking = driving.model_copy(update={"travel_mode": TravelMode.WALKING})
    assert DistanceCache.cache_key(driving) != DistanceCache.cache_key(walking)


def test_fake_location_resolver() -> None:
    resolver = FakeLocationResolver()
    assert resolver.resolve("Mumbai").latitude == 19.076
    assert resolver.resolve("Dubai").longitude == 55.2708


@pytest.mark.asyncio
async def test_mcp_tool_contract(one_to_one_request: DistanceMatrixRequest) -> None:
    from mcp import Client

    service = DistanceService(
        distance_provider=FakeDistanceProvider(),
        cache=DistanceCache(),
    )
    server = create_distance_mcp_server(service)

    async with Client(server) as client:
        tool_result = await client.call_tool(
            "get_distance_matrix",
            {
                "origins": [
                    point.model_dump(mode="json")
                    for point in one_to_one_request.origins
                ],
                "destinations": [
                    point.model_dump(mode="json")
                    for point in one_to_one_request.destinations
                ],
                "travel_mode": one_to_one_request.travel_mode.value,
            },
        )

    payload = tool_result.structured_content
    assert payload["data_status"] == DistanceDataStatus.LIVE.value
    assert payload["routes"]
