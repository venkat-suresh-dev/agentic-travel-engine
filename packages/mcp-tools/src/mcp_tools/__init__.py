"""MCP tool servers for the AI Trip Planner."""

from mcp_tools.distance.mcp_server import create_distance_mcp_server
from mcp_tools.distance.schemas import (
    DistanceDataStatus,
    DistanceMatrixRequest,
    DistanceMatrixResult,
    DistanceRoute,
    DistanceToolMetadata,
    LocationPoint,
    TravelMode,
)
from mcp_tools.distance.service import DistanceService
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
from mcp_tools.places.mcp_server import create_places_mcp_server
from mcp_tools.places.schemas import (
    AttractionCategory,
    AttractionPlace,
    AttractionSearchRequest,
    AttractionSearchResult,
    PlacesDataStatus,
    PlacesToolMetadata,
    RestaurantCuisine,
    RestaurantPlace,
    RestaurantPriceLevel,
    RestaurantSearchRequest,
    RestaurantSearchResult,
    SearchLocation,
)
from mcp_tools.places.service import PlacesService
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
    "DistanceDataStatus",
    "DistanceMatrixRequest",
    "DistanceMatrixResult",
    "DistanceRoute",
    "DistanceService",
    "DistanceToolMetadata",
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
    "LocationPoint",
    "MoneyAmount",
    "PlacesDataStatus",
    "PlacesService",
    "PlacesToolMetadata",
    "RestaurantCuisine",
    "RestaurantPlace",
    "RestaurantPriceLevel",
    "RestaurantSearchRequest",
    "RestaurantSearchResult",
    "SearchLocation",
    "AttractionCategory",
    "AttractionPlace",
    "AttractionSearchRequest",
    "AttractionSearchResult",
    "TravelMode",
    "WeatherDataStatus",
    "WeatherForecastRequest",
    "WeatherForecastResult",
    "WeatherService",
    "WeatherToolMetadata",
    "create_distance_mcp_server",
    "create_flights_mcp_server",
    "create_hotels_mcp_server",
    "create_places_mcp_server",
    "create_weather_mcp_server",
]
