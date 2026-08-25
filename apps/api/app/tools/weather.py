"""Weather tool application boundary."""

from __future__ import annotations

from mcp_tools.weather.schemas import (
    WeatherForecastRequest,
    WeatherForecastResult,
    WeatherToolMetadata,
)
from mcp_tools.weather.service import WeatherService


class WeatherTool:
    """Invoke the MCP-backed weather capability from the application layer."""

    def __init__(self, weather_service: WeatherService | None = None) -> None:
        self._weather_service = weather_service or WeatherService()

    @property
    def weather_service(self) -> WeatherService:
        return self._weather_service

    def get_forecast(
        self,
        request: WeatherForecastRequest,
    ) -> tuple[WeatherForecastResult, WeatherToolMetadata]:
        """Fetch normalized weather facts with provenance metadata."""
        result, metadata = self._weather_service.get_weather_forecast(request)
        return result, metadata
