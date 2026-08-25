"""Graph integration tests for selective trip modifications."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.itinerary.composer.fake import FakeItineraryComposer
from app.modification.schemas import ModificationStatus
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
from tests.itinerary.fixtures import example_valid_itinerary

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)


def _build_service(
    *,
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
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
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


def test_completed_plan_modification_updates_only_target_day(
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
    service = _build_service(
        fake_weather_tool=fake_weather_tool,
        fake_flight_tool=fake_flight_tool,
        fake_airport_resolver=fake_airport_resolver,
        fake_hotel_tool=fake_hotel_tool,
        fake_city_resolver=fake_city_resolver,
        fake_distance_tool=fake_distance_tool,
        fake_location_resolver=fake_location_resolver,
        fake_restaurant_tool=fake_restaurant_tool,
        fake_attraction_tool=fake_attraction_tool,
        fake_currency_tool=fake_currency_tool,
    )

    initial = service.start(COMPLETE_REQUEST, thread_id="mod-pace")
    assert initial.status == GraphStatus.COMPLETE
    assert initial.itinerary_build_result is not None
    assert initial.itinerary_build_result.itinerary is not None
    before = initial.itinerary_build_result.itinerary

    modified = service.resume("mod-pace", "Make day 2 more relaxed.")

    assert modified.status == GraphStatus.COMPLETE
    assert (
        modified.state.get("modification_status") == ModificationStatus.COMPLETE.value
    )
    assert modified.itinerary_build_result is not None
    assert modified.itinerary_build_result.itinerary is not None
    after = modified.itinerary_build_result.itinerary
    assert after.days[0] == before.days[0]
    assert after.days[2:] == before.days[2:]


def test_clarification_flow_still_works_for_incomplete_plan(
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
    service = _build_service(
        fake_weather_tool=fake_weather_tool,
        fake_flight_tool=fake_flight_tool,
        fake_airport_resolver=fake_airport_resolver,
        fake_hotel_tool=fake_hotel_tool,
        fake_city_resolver=fake_city_resolver,
        fake_distance_tool=fake_distance_tool,
        fake_location_resolver=fake_location_resolver,
        fake_restaurant_tool=fake_restaurant_tool,
        fake_attraction_tool=fake_attraction_tool,
        fake_currency_tool=fake_currency_tool,
    )

    incomplete = service.start(
        "Plan a 5-day trip to Dubai for 2 people.", thread_id="clarify"
    )
    assert incomplete.status == GraphStatus.AWAITING_USER

    completed = service.resume(
        "clarify",
        "Budget under ₹1,50,000, departing from Mumbai.",
    )
    assert completed.status == GraphStatus.COMPLETE
    assert completed.itinerary_build_result is not None
    assert completed.itinerary_build_result.itinerary is not None


def test_detector_distinguishes_modification_from_clarification() -> None:
    from app.modification.detector import is_completed_plan_modification

    itinerary = example_valid_itinerary(duration_days=2)
    assert (
        is_completed_plan_modification(
            {
                "user_clarification": "Make day 2 more relaxed.",
                "status": GraphStatus.COMPLETE.value,
                "itinerary": itinerary.model_dump(mode="json"),
                "planning_failed": False,
                "validation": {"is_complete": True, "missing_fields": []},
            }
        )
        is True
    )
    assert (
        is_completed_plan_modification(
            {
                "user_clarification": "Budget is 150000",
                "status": GraphStatus.AWAITING_USER.value,
                "validation": {
                    "is_complete": False,
                    "missing_fields": ["budget_amount"],
                },
            }
        )
        is False
    )
