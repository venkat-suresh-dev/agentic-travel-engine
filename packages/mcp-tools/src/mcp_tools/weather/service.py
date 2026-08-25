"""Weather service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.exceptions import (
    GeocodingError,
    WeatherToolError,
    WeatherValidationError,
)
from mcp_tools.weather.geocoding.base import GeocodingProvider
from mcp_tools.weather.geocoding.open_meteo import OpenMeteoGeocodingProvider
from mcp_tools.weather.providers.base import WeatherProvider
from mcp_tools.weather.providers.open_meteo import OpenMeteoWeatherProvider
from mcp_tools.weather.schemas import (
    WeatherDataStatus,
    WeatherForecastRequest,
    WeatherForecastResult,
    WeatherToolMetadata,
)

OPEN_METEO_SOURCE = "open-meteo"
WEATHER_TOOL_NAME = "get_weather_forecast"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class WeatherService:
    """Coordinate geocoding, provider calls, caching, and provenance metadata."""

    def __init__(
        self,
        *,
        geocoding_provider: GeocodingProvider | None = None,
        weather_provider: WeatherProvider | None = None,
        cache: WeatherCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._geocoding_provider = geocoding_provider or OpenMeteoGeocodingProvider()
        self._weather_provider = weather_provider or OpenMeteoWeatherProvider()
        self._cache = cache or WeatherCache()
        self._retry_backoff_seconds = retry_backoff_seconds

    def get_weather_forecast(
        self,
        request: WeatherForecastRequest,
    ) -> tuple[WeatherForecastResult, WeatherToolMetadata]:
        started = time.perf_counter()
        cache_key = WeatherCache.cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_with_resilience(request, cache_key)
        except WeatherValidationError as exc:
            result = WeatherForecastResult.unavailable(
                location=request.location,
                source=OPEN_METEO_SOURCE,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except GeocodingError as exc:
            result = WeatherForecastResult.unavailable(
                location=request.location,
                source=OPEN_METEO_SOURCE,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except WeatherToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.result.model_copy(
                    update={"data_status": WeatherDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = WeatherForecastResult.unavailable(
                    location=request.location,
                    source=OPEN_METEO_SOURCE,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = WeatherToolMetadata(
            tool_name=WEATHER_TOOL_NAME,
            provider=OPEN_METEO_SOURCE,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def _fetch_with_resilience(
        self,
        request: WeatherForecastRequest,
        cache_key: str,
    ) -> WeatherForecastResult:
        last_error: WeatherToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_live(request, cache_key)
            except WeatherToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_live(
        self,
        request: WeatherForecastRequest,
        cache_key: str,
    ) -> WeatherForecastResult:
        geocoded = self._geocoding_provider.geocode(request.location)
        forecast = self._weather_provider.fetch_forecast(request, geocoded)
        retrieved_at = datetime.now(UTC)
        result = WeatherForecastResult(
            location=geocoded.name,
            latitude=geocoded.latitude,
            longitude=geocoded.longitude,
            source=OPEN_METEO_SOURCE,
            retrieved_at=retrieved_at,
            data_status=WeatherDataStatus.LIVE,
            forecast=forecast,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsWeatherService(Protocol):
    def get_weather_forecast(
        self,
        request: WeatherForecastRequest,
    ) -> tuple[WeatherForecastResult, WeatherToolMetadata]: ...
