"""Flight search service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.exceptions import FlightToolError, FlightValidationError
from mcp_tools.flights.providers.base import FlightProvider
from mcp_tools.flights.schemas import (
    FlightDataStatus,
    FlightSearchRequest,
    FlightSearchResult,
    FlightToolMetadata,
)

AMADEUS_SOURCE = "amadeus"
FLIGHT_TOOL_NAME = "search_flights"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class FlightService:
    """Coordinate provider calls, caching, and provenance metadata."""

    def __init__(
        self,
        *,
        flight_provider: FlightProvider,
        cache: FlightCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
        source: str = AMADEUS_SOURCE,
    ) -> None:
        self._flight_provider = flight_provider
        self._cache = cache or FlightCache()
        self._retry_backoff_seconds = retry_backoff_seconds
        self._source = source

    def search_flights(
        self,
        request: FlightSearchRequest,
    ) -> tuple[FlightSearchResult, FlightToolMetadata]:
        started = time.perf_counter()
        cache_key = FlightCache.cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_with_resilience(request, cache_key)
        except FlightValidationError as exc:
            result = FlightSearchResult.unavailable(
                source=self._source,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except FlightToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.result.model_copy(
                    update={"data_status": FlightDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = FlightSearchResult.unavailable(
                    source=self._source,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = FlightToolMetadata(
            tool_name=FLIGHT_TOOL_NAME,
            provider=self._source,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def _fetch_with_resilience(
        self,
        request: FlightSearchRequest,
        cache_key: str,
    ) -> FlightSearchResult:
        last_error: FlightToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_live(request, cache_key)
            except FlightToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_live(
        self,
        request: FlightSearchRequest,
        cache_key: str,
    ) -> FlightSearchResult:
        offers = self._flight_provider.search_flights(request)
        retrieved_at = datetime.now(UTC)
        result = FlightSearchResult(
            source=self._source,
            retrieved_at=retrieved_at,
            data_status=FlightDataStatus.LIVE,
            offers=offers,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsFlightService(Protocol):
    def search_flights(
        self,
        request: FlightSearchRequest,
    ) -> tuple[FlightSearchResult, FlightToolMetadata]: ...
