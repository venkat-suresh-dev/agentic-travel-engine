"""Typed grounded planning context for itinerary generation."""

from __future__ import annotations

from mcp_tools.currency.schemas import CurrencyConversionResult
from mcp_tools.distance.schemas import DistanceMatrixResult
from mcp_tools.flights.schemas import FlightSearchResult
from mcp_tools.hotels.schemas import HotelSearchResult
from mcp_tools.places.schemas import AttractionSearchResult, RestaurantSearchResult
from mcp_tools.weather.schemas import WeatherForecastResult
from pydantic import BaseModel, ConfigDict

from app.budget.schemas import BudgetResult
from app.domain.trip_request import TripRequest
from app.rag.schemas import RetrievedContext


class ItineraryBuildContext(BaseModel):
    """Grounded inputs for itinerary composition and validation."""

    model_config = ConfigDict(extra="forbid")

    trip_request: TripRequest
    weather_forecast: WeatherForecastResult | None = None
    flight_search: FlightSearchResult | None = None
    hotel_search: HotelSearchResult | None = None
    distance_matrix: DistanceMatrixResult | None = None
    restaurant_search: RestaurantSearchResult | None = None
    attraction_search: AttractionSearchResult | None = None
    currency_conversion: CurrencyConversionResult | None = None
    budget_result: BudgetResult
    retrieved_context: RetrievedContext | None = None
