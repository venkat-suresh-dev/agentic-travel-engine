"""MCP server exposing the weather forecast tool."""

from __future__ import annotations

from datetime import date

from mcp.server import MCPServer

from mcp_tools.weather.schemas import WeatherForecastRequest, WeatherForecastResult
from mcp_tools.weather.service import WeatherService

WEATHER_MCP_SERVER_NAME = "agentic-travel-weather"


def create_weather_mcp_server(
    weather_service: WeatherService | None = None,
) -> MCPServer:
    """Create an MCP server with a single weather forecast tool."""
    service = weather_service or WeatherService()
    server = MCPServer(WEATHER_MCP_SERVER_NAME)

    @server.tool()
    def get_weather_forecast(
        location: str,
        start_date: date,
        end_date: date,
    ) -> WeatherForecastResult:
        """Return a normalized daily weather forecast for a location and date range."""
        request = WeatherForecastRequest(
            location=location,
            start_date=start_date,
            end_date=end_date,
        )
        result, _metadata = service.get_weather_forecast(request)
        return result

    return server


server = create_weather_mcp_server()
