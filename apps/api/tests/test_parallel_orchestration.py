"""Parallel orchestration tests for Phase 3G."""

from __future__ import annotations

import time

from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.schemas import AggregateRunStatus
from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.tools.attractions import AttractionTool
from app.tools.hotels import HotelTool
from mcp_tools.hotels.cache import HotelCache
from mcp_tools.hotels.service import HotelService
from mcp_tools.places.cache import PlacesCache
from mcp_tools.places.service import PlacesService

from tests.fakes.delayed_tools import ConcurrencyTracker, build_delayed_tools
from tests.fakes.hotels_providers import FakeCityCodeResolver, FakeHotelProvider
from tests.fakes.llm import FakeLLMAdapter
from tests.fakes.places_providers import FakePlacesProvider

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)


def _build_service(
    tracker: ConcurrencyTracker,
    *,
    concurrency_limit: int = 4,
    delay_seconds: float = 0.1,
    failing_tools: set[str] | None = None,
) -> TripPlannerAgentService:
    tools = build_delayed_tools(
        tracker,
        delay_seconds=delay_seconds,
        failing_tools=failing_tools,
    )
    limiter = ToolConcurrencyLimiter(concurrency_limit)
    return TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        tool_concurrency_limiter=limiter,
        **tools,
    )


def test_parallel_fan_out_completes_faster_than_sequential_sum(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(
        concurrency_tracker, concurrency_limit=6, delay_seconds=0.1
    )
    started = time.perf_counter()
    result = service.start(COMPLETE_REQUEST, thread_id="parallel-timing")
    elapsed = time.perf_counter() - started

    assert result.status == GraphStatus.COMPLETE
    assert elapsed < 0.45
    assert concurrency_tracker.max_active >= 2


def test_concurrency_limit_is_respected(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(
        concurrency_tracker, concurrency_limit=2, delay_seconds=0.05
    )
    result = service.start(COMPLETE_REQUEST, thread_id="parallel-limit")

    assert result.status == GraphStatus.COMPLETE
    assert concurrency_tracker.max_active <= 2


def test_one_provider_unavailable_yields_partial_success(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(
        concurrency_tracker,
        failing_tools={"hotels"},
    )
    result = service.start(COMPLETE_REQUEST, thread_id="partial-one")

    assert result.status == GraphStatus.COMPLETE
    assert result.aggregate_run_status == AggregateRunStatus.PARTIAL
    assert result.weather_forecast is not None
    assert result.flight_search is not None
    assert result.hotel_search is not None
    assert result.hotel_search.data_status.value == "unavailable"
    assert result.distance_matrix is not None
    assert result.restaurant_search is not None
    assert result.attraction_search is not None


def test_two_providers_unavailable_yields_partial_success(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(
        concurrency_tracker,
        failing_tools={"hotels", "attractions"},
    )
    result = service.start(COMPLETE_REQUEST, thread_id="partial-two")

    assert result.status == GraphStatus.COMPLETE
    assert result.aggregate_run_status == AggregateRunStatus.PARTIAL
    assert result.hotel_search is not None
    assert result.hotel_search.data_status.value == "unavailable"
    assert result.attraction_search is not None
    assert result.attraction_search.data_status.value == "unavailable"
    assert result.weather_forecast is not None
    assert result.flight_search is not None


def test_all_independent_providers_unavailable_yields_failed_aggregate(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(
        concurrency_tracker,
        failing_tools={
            "weather",
            "flights",
            "hotels",
            "distance",
            "restaurants",
            "attractions",
        },
    )
    result = service.start(COMPLETE_REQUEST, thread_id="partial-all-independent")

    assert result.status == GraphStatus.COMPLETE
    assert result.aggregate_run_status == AggregateRunStatus.FAILED


def test_successful_results_preserved_when_another_tool_raises(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    failing_hotel_tool = HotelTool(
        HotelService(
            hotel_provider=FakeHotelProvider(should_fail=True),
            cache=HotelCache(),
        )
    )
    tools = build_delayed_tools(concurrency_tracker, delay_seconds=0.01)
    service = TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        tool_concurrency_limiter=ToolConcurrencyLimiter(4),
        hotel_tool=failing_hotel_tool,
        weather_tool=tools["weather_tool"],
        flight_tool=tools["flight_tool"],
        distance_tool=tools["distance_tool"],
        restaurant_tool=tools["restaurant_tool"],
        attraction_tool=tools["attraction_tool"],
        currency_tool=tools["currency_tool"],
        airport_resolver=tools["airport_resolver"],
        city_resolver=tools["city_resolver"],
        location_resolver=tools["location_resolver"],
    )

    result = service.start(COMPLETE_REQUEST, thread_id="partial-raise")

    assert result.weather_forecast is not None
    assert result.weather_forecast.data_status.value == "live"
    assert result.hotel_search is not None
    assert result.hotel_search.data_status.value == "unavailable"


def test_parallel_execution_preserves_typed_state_and_metadata(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    service = _build_service(concurrency_tracker)
    result = service.start(COMPLETE_REQUEST, thread_id="state-integrity")

    assert result.weather_tool_metadata is not None
    assert result.weather_tool_metadata.tool_name == "get_weather_forecast"
    assert result.flight_tool_metadata is not None
    assert result.flight_tool_metadata.tool_name == "search_flights"
    assert result.hotel_tool_metadata is not None
    assert result.restaurant_tool_metadata is not None
    assert result.attraction_tool_metadata is not None
    # Same-currency INR amounts skip FX; metadata remains unset when skipped.
    assert result.currency_conversion is None
    assert result.currency_tool_metadata is None
    assert result.tool_orchestration_summary is not None
    assert result.tool_orchestration_summary.run_id == "state-integrity"
    assert len(result.tool_orchestration_summary.tool_records) >= 6
    tool_names = [
        record.tool_name for record in result.tool_orchestration_summary.tool_records
    ]
    assert "convert_currency" in tool_names
    assert len(tool_names) == len(set(tool_names))


def test_places_provider_failure_does_not_corrupt_other_metadata(
    concurrency_tracker: ConcurrencyTracker,
) -> None:
    failing_attractions = AttractionTool(
        PlacesService(
            places_provider=FakePlacesProvider(should_fail=True),
            cache=PlacesCache(),
        )
    )
    tools = build_delayed_tools(concurrency_tracker, delay_seconds=0.01)
    service = TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter.from_stub(),
        tool_concurrency_limiter=ToolConcurrencyLimiter(4),
        attraction_tool=failing_attractions,
        weather_tool=tools["weather_tool"],
        flight_tool=tools["flight_tool"],
        hotel_tool=tools["hotel_tool"],
        distance_tool=tools["distance_tool"],
        restaurant_tool=tools["restaurant_tool"],
        currency_tool=tools["currency_tool"],
        airport_resolver=tools["airport_resolver"],
        city_resolver=FakeCityCodeResolver(),
        location_resolver=tools["location_resolver"],
    )

    result = service.start(COMPLETE_REQUEST, thread_id="metadata-isolation")

    assert result.restaurant_tool_metadata is not None
    assert result.restaurant_tool_metadata.tool_name == "search_restaurants"
    assert result.attraction_search is not None
    assert result.attraction_search.data_status.value == "unavailable"
    assert result.aggregate_run_status == AggregateRunStatus.PARTIAL
