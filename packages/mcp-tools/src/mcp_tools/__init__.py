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
from mcp_tools.hotels.mcp_server import create_hotels_mcp_server
from mcp_tools.hotels.schemas import (
    HotelDataStatus,
    HotelOffer,
    HotelSearchRequest,
    HotelSearchResult,
    HotelToolMetadata,
    MoneyAmount,
)
from mcp_tools.hotels.service import HotelService
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
    "HotelDataStatus",
    "HotelOffer",
    "HotelSearchRequest",
    "HotelSearchResult",
    "HotelService",
    "HotelToolMetadata",
    "MoneyAmount",
    "WeatherDataStatus",
    "WeatherForecastRequest",
    "WeatherForecastResult",
    "WeatherService",
    "WeatherToolMetadata",
    "create_flights_mcp_server",
    "create_hotels_mcp_server",
    "create_weather_mcp_server",
]
