"""Fake weather tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.weather import WeatherTool
from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.service import WeatherService

from tests.fakes.weather_providers import FakeGeocodingProvider, FakeWeatherProvider


@pytest.fixture
def fake_weather_service() -> WeatherService:
    return WeatherService(
        geocoding_provider=FakeGeocodingProvider(),
        weather_provider=FakeWeatherProvider(),
        cache=WeatherCache(),
    )


@pytest.fixture
def fake_weather_tool(fake_weather_service: WeatherService) -> WeatherTool:
    return WeatherTool(fake_weather_service)
