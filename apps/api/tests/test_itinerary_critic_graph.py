"""Graph integration tests for the itinerary critic loop."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.critic.constants import MAX_ITINERARY_ATTEMPTS, MAX_ITINERARY_RETRIES
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from mcp_tools.places.schemas import (
    AttractionPlace,
    AttractionSearchRequest,
    RestaurantPlace,
    RestaurantSearchRequest,
)

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.itinerary_composers import FlakyItineraryComposer
from tests.fakes.llm import FakeLLMAdapter
from tests.fakes.places_providers import FakePlacesProvider

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)


class CountingPlacesProvider(FakePlacesProvider):
    def __init__(self) -> None:
        super().__init__()
        self.restaurant_calls = 0
        self.attraction_calls = 0

    def search_restaurants(
        self,
        request: RestaurantSearchRequest,
    ) -> list[RestaurantPlace]:
        self.restaurant_calls += 1
        return super().search_restaurants(request)

    def search_attractions(
        self,
        request: AttractionSearchRequest,
    ) -> list[AttractionPlace]:
        self.attraction_calls += 1
        return super().search_attractions(request)


def _build_counting_service(
    *,
    composer: FakeItineraryComposer | FlakyItineraryComposer,
    counting_provider: CountingPlacesProvider,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_currency_tool: CurrencyTool,
) -> TripPlannerAgentService:
    from mcp_tools.places.cache import PlacesCache
    from mcp_tools.places.service import PlacesService

    places_service = PlacesService(
        places_provider=counting_provider,
        cache=PlacesCache(),
    )
    return TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=RestaurantTool(places_service),
        attraction_tool=AttractionTool(places_service),
        currency_tool=fake_currency_tool,
        itinerary_composer=composer,
    )


def test_critic_retry_succeeds_on_second_attempt(
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
    composer = FlakyItineraryComposer(invalid_until_attempt=1)
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
        itinerary_composer=composer,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="critic-retry-success")

    assert result.status == GraphStatus.COMPLETE
    assert result.planning_failed is False
    assert result.critic_result is not None
    assert result.critic_result.valid is True
    assert composer.attempt_count == 2
    assert result.itinerary_build_result is not None
    assert result.itinerary_build_result.itinerary is not None
    assert result.state.get("itinerary") is not None


def test_critic_retry_succeeds_on_third_attempt(
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
    composer = FlakyItineraryComposer(invalid_until_attempt=2)
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
        itinerary_composer=composer,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="critic-retry-third-success")

    assert result.planning_failed is False
    assert result.critic_result is not None
    assert result.critic_result.valid is True
    assert composer.attempt_count == 3
    assert result.state.get("itinerary") is not None


def test_critic_retry_limit_exhausted_produces_structured_failure(
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
    composer = FlakyItineraryComposer(
        invalid_until_attempt=MAX_ITINERARY_ATTEMPTS,
    )
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
        itinerary_composer=composer,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="critic-retry-failure")

    assert result.status == GraphStatus.COMPLETE
    assert result.planning_failed is True
    assert composer.attempt_count == MAX_ITINERARY_ATTEMPTS
    assert result.critic_result is not None
    assert result.critic_result.valid is False
    assert result.state.get("itinerary") is None
    assert result.state.get("itinerary_candidate") is not None
    assert result.state.get("planning_failure") is not None


def test_critic_retries_do_not_reinvoke_places_providers(
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_currency_tool: CurrencyTool,
) -> None:
    counting_provider = CountingPlacesProvider()
    composer = FlakyItineraryComposer(invalid_until_attempt=1)
    service = _build_counting_service(
        composer=composer,
        counting_provider=counting_provider,
        fake_weather_tool=fake_weather_tool,
        fake_flight_tool=fake_flight_tool,
        fake_airport_resolver=fake_airport_resolver,
        fake_hotel_tool=fake_hotel_tool,
        fake_city_resolver=fake_city_resolver,
        fake_distance_tool=fake_distance_tool,
        fake_location_resolver=fake_location_resolver,
        fake_currency_tool=fake_currency_tool,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="critic-no-provider-rerun")

    assert result.planning_failed is False
    assert counting_provider.restaurant_calls == 1
    assert counting_provider.attraction_calls == 1
    assert composer.attempt_count == 2


def test_retry_constants_match_documented_attempt_budget() -> None:
    assert MAX_ITINERARY_RETRIES == 2
    assert MAX_ITINERARY_ATTEMPTS == 3
