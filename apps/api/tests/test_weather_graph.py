"""Graph integration tests for the weather vertical slice."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.tools.attractions import AttractionTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."


def test_complete_request_stores_weather_in_graph_state(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="weather-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.weather_forecast is not None
    assert result.weather_forecast.data_status.value == "live"
    assert result.weather_forecast.forecast
    assert result.weather_tool_metadata is not None
    assert result.weather_tool_metadata.tool_name == "get_weather_forecast"
    assert result.weather_tool_metadata.provider == "open-meteo"


def test_incomplete_request_does_not_fetch_weather(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
    )

    result = service.start(INCOMPLETE_REQUEST, thread_id="weather-incomplete")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.weather_forecast is None
    assert result.weather_tool_metadata is None
