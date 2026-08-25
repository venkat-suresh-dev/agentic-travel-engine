"""Graph integration tests for deterministic budget computation."""

from __future__ import annotations

from decimal import Decimal

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
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


def test_complete_request_includes_authoritative_budget_result(
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
    )

    result = service.start(COMPLETE_REQUEST, thread_id="budget-graph-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.budget_result is not None
    assert result.budget_result.is_authoritative is True
    assert result.budget_result.currency == "INR"
    assert result.budget_result.flight_cost == Decimal("45000.00")
    assert result.budget_result.hotel_cost == Decimal("2250.00")
    assert result.budget_result.total_cost > Decimal("0")
    assert result.budget_result.remaining == (
        result.budget_result.budget_amount - result.budget_result.total_cost
    )


def test_budget_result_is_deterministic_across_graph_runs(
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
    )

    first = service.start(COMPLETE_REQUEST, thread_id="budget-graph-deterministic-1")
    second = service.start(COMPLETE_REQUEST, thread_id="budget-graph-deterministic-2")

    assert first.budget_result is not None
    assert second.budget_result is not None
    assert first.budget_result == second.budget_result
