"""Graph integration tests for the currency vertical slice."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.service import FlightService

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver, FakeFlightProvider
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."


@pytest.fixture
def fake_usd_flight_tool() -> FlightTool:
    return FlightTool(
        FlightService(
            flight_provider=FakeFlightProvider(price_currency="USD"),
            cache=FlightCache(),
        )
    )


def test_complete_request_skips_conversion_when_all_amounts_match_budget_currency(
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
    fake_currency_tool: CurrencyTool,
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
        currency_tool=fake_currency_tool,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="currency-complete-inr")

    assert result.status == GraphStatus.COMPLETE
    assert result.flight_search is not None
    assert result.flight_search.offers[0].price_currency == "INR"
    assert result.hotel_search is not None
    assert result.hotel_search.hotels[0].total_price is not None
    assert result.hotel_search.hotels[0].total_price.currency == "INR"
    # Identity INR→INR conversion is skipped; amounts already match trip currency.
    assert result.currency_conversion is None
    assert result.budget_result is not None
    assert result.budget_result.currency == "INR"


def test_complete_request_converts_foreign_flight_price_without_overwriting_source(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_usd_flight_tool: FlightTool,
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
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_usd_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
        currency_tool=fake_currency_tool,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="currency-complete-usd")

    assert result.status == GraphStatus.COMPLETE
    assert result.flight_search is not None
    assert result.flight_search.offers[0].price_currency == "USD"
    assert result.flight_search.offers[0].price_amount == Decimal("45000")
    assert result.currency_conversion is not None
    assert result.currency_conversion.base_currency == "USD"
    assert result.currency_conversion.quote_currency == "INR"
    assert result.currency_conversion.input_amount == Decimal("45000.00")
    assert result.currency_conversion.converted_amount == Decimal("3740400.00")
    assert result.currency_conversion.source == "frankfurter"
    assert result.currency_conversion.source_context == "flight_lowest_offer"
    assert result.currency_conversion.source_offer_id == "fake-1"


def test_incomplete_request_does_not_convert_currency(
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
    fake_currency_tool: CurrencyTool,
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
        currency_tool=fake_currency_tool,
    )

    result = service.start(INCOMPLETE_REQUEST, thread_id="currency-incomplete")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.currency_conversion is None
    assert result.currency_tool_metadata is None
