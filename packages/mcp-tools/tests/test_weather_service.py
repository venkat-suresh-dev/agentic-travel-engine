"""Weather MCP tool tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.exceptions import WeatherProviderError
from mcp_tools.weather.mcp_server import create_weather_mcp_server
from mcp_tools.weather.schemas import (
    WeatherDataStatus,
    WeatherForecastRequest,
)
from mcp_tools.weather.service import WeatherService
from tests.fakes import (
    FailingGeocodingProvider,
    FakeGeocodingProvider,
    FakeWeatherProvider,
)


@pytest.fixture
def request_window() -> WeatherForecastRequest:
    start = date.today()
    return WeatherForecastRequest(
        location="Dubai",
        start_date=start,
        end_date=start + timedelta(days=4),
    )


def test_live_weather_response_has_provenance(
    request_window: WeatherForecastRequest,
) -> None:
    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=WeatherCache(),
    )

    result, metadata = service.get_weather_forecast(request_window)

    assert result.data_status is WeatherDataStatus.LIVE
    assert result.source == "open-meteo"
    assert result.retrieved_at is not None
    assert result.forecast
    assert metadata.tool_name == "get_weather_forecast"
    assert metadata.provider == "open-meteo"
    assert metadata.cache_status == "miss"


def test_cache_hit_returns_cached_status(
    request_window: WeatherForecastRequest,
) -> None:
    cache = WeatherCache(ttl_seconds=1800)
    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=cache,
    )
    service.get_weather_forecast(request_window)

    failing_service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(should_fail=True),
        cache=cache,
    )
    result, metadata = failing_service.get_weather_forecast(request_window)

    assert result.data_status is WeatherDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_provider_failure_without_cache_is_unavailable(
    request_window: WeatherForecastRequest,
) -> None:
    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(should_fail=True),
        cache=WeatherCache(),
    )

    result, _metadata = service.get_weather_forecast(request_window)

    assert result.data_status is WeatherDataStatus.UNAVAILABLE
    assert result.forecast == []
    assert result.error_message is not None


def test_provider_retries_once_before_failure(
    request_window: WeatherForecastRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    class FlakyWeatherProvider(FakeWeatherProvider):
        def fetch_forecast(self, request, location):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise WeatherProviderError("temporary failure")
            return super().fetch_forecast(request, location)

    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FlakyWeatherProvider(),
        cache=WeatherCache(),
    )

    result, _metadata = service.get_weather_forecast(request_window)

    assert attempts["count"] == 2
    assert result.data_status is WeatherDataStatus.LIVE


def test_malformed_provider_response_is_unavailable(
    request_window: WeatherForecastRequest,
) -> None:
    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(malformed=True),
        cache=WeatherCache(),
    )

    result, _metadata = service.get_weather_forecast(request_window)

    assert result.data_status is WeatherDataStatus.UNAVAILABLE


def test_geocoding_failure_is_unavailable(
    request_window: WeatherForecastRequest,
) -> None:
    service = WeatherService(
        geocoding_provider=FailingGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=WeatherCache(),
    )

    result, _metadata = service.get_weather_forecast(request_window)

    assert result.data_status is WeatherDataStatus.UNAVAILABLE
    assert "location not found" in (result.error_message or "")


def test_invalid_request_dates_raise_validation_error() -> None:
    with pytest.raises(ValueError):
        WeatherForecastRequest(
            location="Dubai",
            start_date=date(2026, 12, 10),
            end_date=date(2026, 12, 1),
        )


def test_cache_expiry_allows_new_live_fetch(
    request_window: WeatherForecastRequest,
) -> None:
    cache = WeatherCache(ttl_seconds=1)
    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=cache,
    )
    first, _ = service.get_weather_forecast(request_window)

    key = WeatherCache.cache_key(request_window)
    entry = cache.get(key)
    assert entry is not None
    cache._entries[key] = type(entry)(
        result=entry.result,
        stored_at=datetime.now(UTC) - timedelta(seconds=2),
    )

    second, metadata = service.get_weather_forecast(request_window)

    assert second.data_status is WeatherDataStatus.LIVE
    assert second.retrieved_at >= first.retrieved_at
    assert metadata.cache_status == "miss"


def test_provider_timeout_retries_once_then_unavailable(
    request_window: WeatherForecastRequest,
) -> None:
    attempts = {"count": 0}

    class TimeoutWeatherProvider(FakeWeatherProvider):
        def fetch_forecast(self, request, location):  # type: ignore[no-untyped-def]
            attempts["count"] += 1
            from mcp_tools.weather.exceptions import WeatherProviderTimeoutError

            raise WeatherProviderTimeoutError("simulated timeout")

    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=TimeoutWeatherProvider(),
        cache=WeatherCache(),
    )

    result, _metadata = service.get_weather_forecast(request_window)

    assert attempts["count"] == 2
    assert result.data_status is WeatherDataStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_mcp_tool_contract(request_window: WeatherForecastRequest) -> None:
    from mcp import Client

    service = WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=WeatherCache(),
    )
    server = create_weather_mcp_server(service)

    async with Client(server) as client:
        tool_result = await client.call_tool(
            "get_weather_forecast",
            {
                "location": request_window.location,
                "start_date": request_window.start_date.isoformat(),
                "end_date": request_window.end_date.isoformat(),
            },
        )

    payload = tool_result.structured_content
    assert payload["data_status"] == WeatherDataStatus.LIVE.value
    assert payload["forecast"]
