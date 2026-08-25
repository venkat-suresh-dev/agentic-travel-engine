"""Graph integration tests for itinerary generation."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.itinerary.composer.fake import FakeItineraryComposer
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
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


def test_complete_request_produces_validated_itinerary(
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
    fake_currency_tool: CurrencyTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
        currency_tool=fake_currency_tool,
        itinerary_composer=FakeItineraryComposer(),
    )

    result = service.start(COMPLETE_REQUEST, thread_id="itinerary-graph-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.planning_failed is False
    assert result.critic_result is not None
    assert result.critic_result.valid is True
    assert result.itinerary_build_result is not None
    assert result.itinerary_build_result.success is True
    assert result.itinerary_build_result.itinerary is not None
    assert len(result.itinerary_build_result.itinerary.days) == 5
    assert result.itinerary_build_result.validation.is_valid is True
    assert result.state.get("itinerary") is not None
    assert result.state.get("itinerary_draft") is not None


def test_incomplete_request_does_not_generate_itinerary(
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
    fake_currency_tool: CurrencyTool,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
        currency_tool=fake_currency_tool,
        itinerary_composer=FakeItineraryComposer(),
    )

    result = service.start(INCOMPLETE_REQUEST, thread_id="itinerary-graph-incomplete")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.state.get("itinerary") is None
    assert result.state.get("itinerary_build_success") is None
