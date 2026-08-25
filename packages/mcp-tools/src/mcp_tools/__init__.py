"""MCP tool servers for the AI Trip Planner."""

from mcp_tools.flights.mcp_server import create_flights_mcp_server
from mcp_tools.flights.schemas import (
    CabinClass,
    FlightDataStatus,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResult,
    FlightToolMetadata,
)
from mcp_tools.flights.service import FlightService
from mcp_tools.weather.mcp_server import create_weather_mcp_server
from mcp_tools.weather.schemas import (
    DailyForecast,
    WeatherDataStatus,
    WeatherForecastRequest,
    WeatherForecastResult,
    WeatherToolMetadata,
)
from mcp_tools.weather.service import WeatherService

__all__ = [
    "CabinClass",
    "DailyForecast",
    "FlightDataStatus",
    "FlightOffer",
    "FlightSearchRequest",
    "FlightSearchResult",
    "FlightService",
    "FlightToolMetadata",
    "WeatherDataStatus",
    "WeatherForecastRequest",
    "WeatherForecastResult",
    "WeatherService",
    "WeatherToolMetadata",
    "create_flights_mcp_server",
    "create_weather_mcp_server",
]
