"""Distance matrix service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from mcp_tools.distance.cache import DistanceCache
from mcp_tools.distance.exceptions import DistanceToolError, DistanceValidationError
from mcp_tools.distance.providers.base import DistanceProvider
from mcp_tools.distance.schemas import (
    DistanceDataStatus,
    DistanceMatrixRequest,
    DistanceMatrixResult,
    DistanceToolMetadata,
)

OPENROUTESERVICE_SOURCE = "openrouteservice"
DISTANCE_TOOL_NAME = "get_distance_matrix"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class DistanceService:
    """Coordinate provider calls, caching, and provenance metadata."""

    def __init__(
        self,
        *,
        distance_provider: DistanceProvider,
        cache: DistanceCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._distance_provider = distance_provider
        self._cache = cache or DistanceCache()
        self._retry_backoff_seconds = retry_backoff_seconds

    def get_distance_matrix(
        self,
        request: DistanceMatrixRequest,
    ) -> tuple[DistanceMatrixResult, DistanceToolMetadata]:
        started = time.perf_counter()
        cache_key = DistanceCache.cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_with_resilience(request, cache_key)
        except DistanceValidationError as exc:
            result = DistanceMatrixResult.unavailable(
                source=OPENROUTESERVICE_SOURCE,
                retrieved_at=datetime.now(UTC),
                travel_mode=request.travel_mode,
                error_message=str(exc),
            )
        except DistanceToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.result.model_copy(
                    update={"data_status": DistanceDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = DistanceMatrixResult.unavailable(
                    source=OPENROUTESERVICE_SOURCE,
                    retrieved_at=datetime.now(UTC),
                    travel_mode=request.travel_mode,
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = DistanceToolMetadata(
            tool_name=DISTANCE_TOOL_NAME,
            provider=OPENROUTESERVICE_SOURCE,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def _fetch_with_resilience(
        self,
        request: DistanceMatrixRequest,
        cache_key: str,
    ) -> DistanceMatrixResult:
        last_error: DistanceToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_live(request, cache_key)
            except DistanceToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_live(
        self,
        request: DistanceMatrixRequest,
        cache_key: str,
    ) -> DistanceMatrixResult:
        routes = self._distance_provider.get_distance_matrix(request)
        retrieved_at = datetime.now(UTC)
        result = DistanceMatrixResult(
            source=OPENROUTESERVICE_SOURCE,
            retrieved_at=retrieved_at,
            data_status=DistanceDataStatus.LIVE,
            travel_mode=request.travel_mode,
            routes=routes,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsDistanceService(Protocol):
    def get_distance_matrix(
        self,
        request: DistanceMatrixRequest,
    ) -> tuple[DistanceMatrixResult, DistanceToolMetadata]: ...
