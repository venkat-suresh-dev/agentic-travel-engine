"""Graph integration tests for the flight vertical slice."""

from __future__ import annotations

from app.agent.service import TripPlannerAgentService
from app.agent.state import GraphStatus
from app.tools.flights import FlightTool
from app.tools.weather import WeatherTool

from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.llm import FakeLLMAdapter

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."


def test_complete_request_stores_flights_in_graph_state(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
    )

    result = service.start(COMPLETE_REQUEST, thread_id="flights-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.weather_forecast is not None
    assert result.flight_search is not None
    assert result.flight_search.data_status.value == "live"
    assert result.flight_search.offers
    assert result.flight_tool_metadata is not None
    assert result.flight_tool_metadata.tool_name == "search_flights"


def test_incomplete_request_does_not_fetch_flights(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
) -> None:
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
    )

    result = service.start(INCOMPLETE_REQUEST, thread_id="flights-incomplete")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.flight_search is None
    assert result.flight_tool_metadata is None
