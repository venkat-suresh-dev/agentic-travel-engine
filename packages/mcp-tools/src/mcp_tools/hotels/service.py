"""Hotel search service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.exceptions import HotelToolError, HotelValidationError
from mcp_tools.hotels.providers.base import HotelProvider
from mcp_tools.hotels.schemas import (
    HotelDataStatus,
    HotelSearchRequest,
    HotelSearchResult,
    HotelToolMetadata,
)

AMADEUS_SOURCE = "amadeus"
HOTEL_TOOL_NAME = "search_hotels"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class HotelService:
    """Coordinate provider calls, caching, and provenance metadata."""

    def __init__(
        self,
        *,
        hotel_provider: HotelProvider,
        cache: HotelCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
        source: str = AMADEUS_SOURCE,
    ) -> None:
        self._hotel_provider = hotel_provider
        self._cache = cache or HotelCache()
        self._retry_backoff_seconds = retry_backoff_seconds
        self._source = source

    def search_hotels(
        self,
        request: HotelSearchRequest,
    ) -> tuple[HotelSearchResult, HotelToolMetadata]:
        started = time.perf_counter()
        cache_key = HotelCache.cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_with_resilience(request, cache_key)
        except HotelValidationError as exc:
            result = HotelSearchResult.unavailable(
                source=self._source,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except HotelToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.result.model_copy(
                    update={"data_status": HotelDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = HotelSearchResult.unavailable(
                    source=self._source,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = HotelToolMetadata(
            tool_name=HOTEL_TOOL_NAME,
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
        request: HotelSearchRequest,
        cache_key: str,
    ) -> HotelSearchResult:
        last_error: HotelToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_live(request, cache_key)
            except HotelToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_live(
        self,
        request: HotelSearchRequest,
        cache_key: str,
    ) -> HotelSearchResult:
        hotels = self._hotel_provider.search_hotels(request)
        retrieved_at = datetime.now(UTC)
        result = HotelSearchResult(
            source=self._source,
            retrieved_at=retrieved_at,
            data_status=HotelDataStatus.LIVE,
            hotels=hotels,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsHotelService(Protocol):
    def search_hotels(
        self,
        request: HotelSearchRequest,
    ) -> tuple[HotelSearchResult, HotelToolMetadata]: ...
