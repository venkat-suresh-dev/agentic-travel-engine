"""Places search service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.exceptions import PlacesToolError, PlacesValidationError
from mcp_tools.places.providers.base import PlacesProvider
from mcp_tools.places.schemas import (
    AttractionSearchRequest,
    AttractionSearchResult,
    PlacesDataStatus,
    PlacesToolMetadata,
    RestaurantSearchRequest,
    RestaurantSearchResult,
)

GOOGLE_PLACES_SOURCE = "google-places"
RESTAURANT_TOOL_NAME = "search_restaurants"
ATTRACTION_TOOL_NAME = "search_attractions"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class PlacesService:
    """Coordinate provider calls, caching, and provenance metadata."""

    def __init__(
        self,
        *,
        places_provider: PlacesProvider,
        cache: PlacesCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._places_provider = places_provider
        self._cache = cache or PlacesCache()
        self._retry_backoff_seconds = retry_backoff_seconds

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> tuple[RestaurantSearchResult, PlacesToolMetadata]:
        started = time.perf_counter()
        cache_key = PlacesCache.restaurant_cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_restaurants_with_resilience(request, cache_key)
        except PlacesValidationError as exc:
            result = RestaurantSearchResult.unavailable(
                source=GOOGLE_PLACES_SOURCE,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except PlacesToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached.result, RestaurantSearchResult):
                result = cached.result.model_copy(
                    update={"data_status": PlacesDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = RestaurantSearchResult.unavailable(
                    source=GOOGLE_PLACES_SOURCE,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = PlacesToolMetadata(
            tool_name=RESTAURANT_TOOL_NAME,
            provider=GOOGLE_PLACES_SOURCE,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> tuple[AttractionSearchResult, PlacesToolMetadata]:
        started = time.perf_counter()
        cache_key = PlacesCache.attraction_cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_attractions_with_resilience(request, cache_key)
        except PlacesValidationError as exc:
            result = AttractionSearchResult.unavailable(
                source=GOOGLE_PLACES_SOURCE,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except PlacesToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None and isinstance(cached.result, AttractionSearchResult):
                result = cached.result.model_copy(
                    update={"data_status": PlacesDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = AttractionSearchResult.unavailable(
                    source=GOOGLE_PLACES_SOURCE,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = PlacesToolMetadata(
            tool_name=ATTRACTION_TOOL_NAME,
            provider=GOOGLE_PLACES_SOURCE,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def _fetch_restaurants_with_resilience(
        self,
        request: RestaurantSearchRequest,
        cache_key: str,
    ) -> RestaurantSearchResult:
        last_error: PlacesToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_restaurants_live(request, cache_key)
            except PlacesToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_attractions_with_resilience(
        self,
        request: AttractionSearchRequest,
        cache_key: str,
    ) -> AttractionSearchResult:
        last_error: PlacesToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_attractions_live(request, cache_key)
            except PlacesToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_restaurants_live(
        self,
        request: RestaurantSearchRequest,
        cache_key: str,
    ) -> RestaurantSearchResult:
        restaurants = self._places_provider.search_restaurants(request)
        retrieved_at = datetime.now(UTC)
        result = RestaurantSearchResult(
            source=GOOGLE_PLACES_SOURCE,
            retrieved_at=retrieved_at,
            data_status=PlacesDataStatus.LIVE,
            restaurants=restaurants,
        )
        self._cache.set(cache_key, result)
        return result

    def _fetch_attractions_live(
        self,
        request: AttractionSearchRequest,
        cache_key: str,
    ) -> AttractionSearchResult:
        attractions = self._places_provider.search_attractions(request)
        retrieved_at = datetime.now(UTC)
        result = AttractionSearchResult(
            source=GOOGLE_PLACES_SOURCE,
            retrieved_at=retrieved_at,
            data_status=PlacesDataStatus.LIVE,
            attractions=attractions,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsPlacesService(Protocol):
    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> tuple[RestaurantSearchResult, PlacesToolMetadata]: ...

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> tuple[AttractionSearchResult, PlacesToolMetadata]: ...
