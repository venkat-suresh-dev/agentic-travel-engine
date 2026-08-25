"""Delayed and instrumented tool fakes for parallel orchestration tests."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock
from typing import Any, TypedDict, cast

import pytest
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from mcp_tools.currency.cache import CurrencyCache
from mcp_tools.currency.service import CurrencyService
from mcp_tools.distance.cache import DistanceCache
from mcp_tools.distance.service import DistanceService
from mcp_tools.flights.cache import FlightCache
from mcp_tools.flights.service import FlightService
from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.service import HotelService
from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.service import PlacesService
from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.service import WeatherService

from tests.fakes.currency_providers import FakeCurrencyRateProvider
from tests.fakes.distance_providers import FakeDistanceProvider, FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver, FakeFlightProvider
from tests.fakes.hotels_providers import FakeCityCodeResolver, FakeHotelProvider
from tests.fakes.places_providers import FakePlacesProvider
from tests.fakes.weather_providers import FakeGeocodingProvider, FakeWeatherProvider


class ConcurrencyTracker:
    """Track active concurrent tool executions during tests."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.active = 0
        self.max_active = 0

    def enter(self) -> None:
        with self._lock:
            self.active += 1
            if self.active > self.max_active:
                self.max_active = self.active

    def exit(self) -> None:
        with self._lock:
            self.active -= 1


class DelayedToolBundle(TypedDict):
    weather_tool: WeatherTool
    flight_tool: FlightTool
    hotel_tool: HotelTool
    distance_tool: DistanceTool
    restaurant_tool: RestaurantTool
    attraction_tool: AttractionTool
    currency_tool: CurrencyTool
    airport_resolver: FakeAirportCodeResolver
    city_resolver: FakeCityCodeResolver
    location_resolver: FakeLocationResolver


def _delay_wrap(
    provider: object,
    method_name: str,
    *,
    delay_seconds: float,
    tracker: ConcurrencyTracker,
) -> object:
    original: Callable[..., Any] = getattr(provider, method_name)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        tracker.enter()
        try:
            time.sleep(delay_seconds)
            return original(*args, **kwargs)
        finally:
            tracker.exit()

    setattr(provider, method_name, wrapped)
    return provider


@pytest.fixture
def concurrency_tracker() -> ConcurrencyTracker:
    return ConcurrencyTracker()


def build_delayed_tools(
    tracker: ConcurrencyTracker,
    *,
    delay_seconds: float = 0.1,
    failing_tools: set[str] | None = None,
) -> DelayedToolBundle:
    """Build delayed fake tools for orchestration tests."""
    failures = failing_tools or set()

    weather_provider = FakeWeatherProvider(
        should_fail="weather" in failures,
    )
    _delay_wrap(
        weather_provider,
        "fetch_forecast",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    flight_provider = FakeFlightProvider(
        should_fail="flights" in failures,
    )
    _delay_wrap(
        flight_provider,
        "search_flights",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    hotel_provider = FakeHotelProvider(should_fail="hotels" in failures)
    _delay_wrap(
        hotel_provider,
        "search_hotels",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    distance_provider = FakeDistanceProvider(should_fail="distance" in failures)
    _delay_wrap(
        distance_provider,
        "get_distance_matrix",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    restaurant_provider = FakePlacesProvider(should_fail="restaurants" in failures)
    _delay_wrap(
        restaurant_provider,
        "search_restaurants",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    attraction_provider = FakePlacesProvider(should_fail="attractions" in failures)
    _delay_wrap(
        attraction_provider,
        "search_attractions",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    currency_provider = FakeCurrencyRateProvider(should_fail="currency" in failures)
    _delay_wrap(
        currency_provider,
        "get_exchange_rate",
        delay_seconds=delay_seconds,
        tracker=tracker,
    )

    return cast(
        DelayedToolBundle,
        {
            "weather_tool": WeatherTool(
                WeatherService(
                    geocoding_provider=FakeGeocodingProvider(),
                    weather_provider=weather_provider,
                    cache=WeatherCache(),
                )
            ),
            "flight_tool": FlightTool(
                FlightService(
                    flight_provider=flight_provider,
                    cache=FlightCache(),
                )
            ),
            "hotel_tool": HotelTool(
                HotelService(
                    hotel_provider=hotel_provider,
                    cache=HotelCache(),
                )
            ),
            "distance_tool": DistanceTool(
                DistanceService(
                    distance_provider=distance_provider,
                    cache=DistanceCache(),
                )
            ),
            "restaurant_tool": RestaurantTool(
                PlacesService(
                    places_provider=restaurant_provider,
                    cache=PlacesCache(),
                )
            ),
            "attraction_tool": AttractionTool(
                PlacesService(
                    places_provider=attraction_provider,
                    cache=PlacesCache(),
                )
            ),
            "currency_tool": CurrencyTool(
                CurrencyService(
                    currency_provider=currency_provider,
                    cache=CurrencyCache(),
                )
            ),
            "airport_resolver": FakeAirportCodeResolver(),
            "city_resolver": FakeCityCodeResolver(),
            "location_resolver": FakeLocationResolver(),
        },
    )
