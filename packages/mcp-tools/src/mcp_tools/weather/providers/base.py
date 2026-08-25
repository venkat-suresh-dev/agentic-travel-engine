"""Weather provider abstractions."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.weather.geocoding.base import GeocodedLocation
from mcp_tools.weather.schemas import DailyForecast, WeatherForecastRequest


class WeatherProvider(Protocol):
    """Fetch normalized daily forecasts for a resolved location."""

    def fetch_forecast(
        self,
        request: WeatherForecastRequest,
        location: GeocodedLocation,
    ) -> list[DailyForecast]: ...
