"""Tests for the trip planner LangGraph foundation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.agent.graph import compile_trip_planner_graph
from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.routing import route_after_validation
from app.agent.service import TripPlannerAgentService
from app.agent.state import AgentState, GraphStatus
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult
from app.tools.attractions import AttractionTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from pydantic import ValidationError

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.extract_stub import extract_from_text
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."


@pytest.fixture
def fake_adapter() -> FakeLLMAdapter:
    return FakeLLMAdapter.from_stub()


@pytest.fixture
def agent_service(
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
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
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


def test_trip_request_schema_rejects_invalid_state() -> None:
    with pytest.raises(ValidationError):
        TripRequest.model_validate(
            {
                "destination": "Dubai",
                "duration_days": 0,
                "travelers": 2,
            }
        )

    with pytest.raises(ValidationError):
        TripRequest.model_validate(
            {
                "destination": "Dubai",
                "start_date": "2026-12-10",
                "end_date": "2026-12-01",
            }
        )


def test_extract_from_text_parses_complete_request() -> None:
    trip_request = extract_from_text(COMPLETE_REQUEST)

    assert trip_request.destination == "Dubai"
    assert trip_request.duration_days == 5
    assert trip_request.travelers == 2
    assert trip_request.budget_amount == Decimal("150000")
    assert trip_request.budget_currency == "INR"
    assert trip_request.departure_city == "Mumbai"


def test_extract_from_text_does_not_invent_missing_values() -> None:
    trip_request = extract_from_text(INCOMPLETE_REQUEST)

    assert trip_request.destination == "Dubai"
    assert trip_request.duration_days == 5
    assert trip_request.travelers == 2
    assert trip_request.budget_amount is None
    assert trip_request.departure_city is None


def test_extract_requirements_node_is_independently_callable(
    fake_adapter: FakeLLMAdapter,
) -> None:
    extract_requirements = build_extract_requirements_node(fake_adapter)
    state: AgentState = {"user_request": INCOMPLETE_REQUEST, "messages": []}
    updated = extract_requirements(state)

    assert updated["status"] == GraphStatus.VALIDATING.value
    assert updated["trip_request"] is not None
    assert updated["messages"][-1]["content"] == INCOMPLETE_REQUEST


def test_validate_requirements_node_detects_missing_fields() -> None:
    trip_request = extract_from_text(INCOMPLETE_REQUEST)
    state: AgentState = {
        "trip_request": trip_request.model_dump(mode="json"),
    }

    updated = validate_requirements(state)
    validation = ValidationResult.model_validate(updated["validation"])

    assert validation.is_complete is False
    assert "budget_amount" in validation.missing_fields
    assert "departure_city" in validation.missing_fields
    assert updated["status"] == GraphStatus.AWAITING_USER.value


def test_validate_requirements_node_marks_complete_request() -> None:
    trip_request = extract_from_text(COMPLETE_REQUEST)
    state: AgentState = {
        "trip_request": trip_request.model_dump(mode="json"),
    }

    updated = validate_requirements(state)
    validation = ValidationResult.model_validate(updated["validation"])

    assert validation.is_complete is True
    assert validation.missing_fields == []
    assert updated["status"] == GraphStatus.COMPLETE.value


def test_ask_user_node_returns_structured_clarification() -> None:
    state: AgentState = {
        "validation": ValidationResult(
            is_complete=False,
            missing_fields=["budget_amount", "departure_city"],
        ).model_dump(mode="json"),
    }

    updated = ask_user(state)
    clarification = ClarificationRequest.model_validate(updated["clarification"])

    assert clarification.missing_fields == ["budget_amount", "departure_city"]
    assert "budget_amount" in clarification.prompts
    assert "departure_city" in clarification.prompts


def test_route_after_validation_routes_incomplete_to_ask_user() -> None:
    state: AgentState = {
        "validation": ValidationResult(
            is_complete=False,
            missing_fields=["budget_amount"],
        ).model_dump(mode="json"),
    }

    assert route_after_validation(state) == "ask_user"


def test_route_after_validation_routes_complete_to_fetch_weather() -> None:
    state: AgentState = {
        "validation": ValidationResult(
            is_complete=True,
            missing_fields=[],
        ).model_dump(mode="json"),
    }

    assert route_after_validation(state) == "fetch_weather"


def test_graph_complete_request_reaches_terminal_state_without_ask_user(
    agent_service: TripPlannerAgentService,
) -> None:
    result = agent_service.start(COMPLETE_REQUEST, thread_id="complete-thread")

    assert result.status == GraphStatus.COMPLETE
    assert result.trip_request is not None
    assert result.trip_request.destination == "Dubai"
    assert result.trip_request.budget_amount == Decimal("150000")
    assert result.clarification is None
    assert result.validation is not None
    assert result.validation.is_complete is True
    assert result.weather_forecast is not None
    assert result.weather_forecast.data_status.value == "live"
    assert result.weather_tool_metadata is not None
    assert result.weather_tool_metadata.tool_name == "get_weather_forecast"
    assert result.flight_search is not None
    assert result.flight_search.data_status.value == "live"
    assert result.flight_tool_metadata is not None


def test_graph_incomplete_request_routes_to_ask_user(
    agent_service: TripPlannerAgentService,
) -> None:
    result = agent_service.start(INCOMPLETE_REQUEST, thread_id="incomplete-thread")

    assert result.status == GraphStatus.AWAITING_USER
    assert result.validation is not None
    assert result.validation.is_complete is False
    assert result.clarification is not None
    assert "budget_amount" in result.clarification.missing_fields
    assert "departure_city" in result.clarification.missing_fields
    assert result.weather_forecast is None
    assert result.flight_search is None


def test_graph_missing_budget(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a 5-day trip to Dubai for 2 people departing from Mumbai.",
        thread_id="missing-budget-thread",
    )

    assert result.status == GraphStatus.AWAITING_USER
    assert result.validation is not None
    assert result.validation.missing_fields == ["budget_amount"]


def test_graph_missing_dates(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a trip to Dubai for 2 people under ₹1,50,000 departing from Mumbai.",
        thread_id="missing-dates-thread",
    )

    assert result.status == GraphStatus.AWAITING_USER
    assert result.validation is not None
    assert "duration_days" in result.validation.missing_fields


def test_graph_missing_destination(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a 5-day trip for 2 people under ₹1,50,000 departing from Mumbai.",
        thread_id="missing-destination-thread",
    )

    assert result.status == GraphStatus.AWAITING_USER
    assert result.validation is not None
    assert "destination" in result.validation.missing_fields


def test_graph_resume_preserves_existing_requirements(
    agent_service: TripPlannerAgentService,
) -> None:
    thread_id = "resume-thread"
    initial = agent_service.start(INCOMPLETE_REQUEST, thread_id=thread_id)

    assert initial.trip_request is not None
    assert initial.trip_request.destination == "Dubai"
    assert initial.trip_request.travelers == 2

    resumed = agent_service.resume(
        thread_id,
        "My budget is under ₹1,50,000 and I am departing from Mumbai.",
    )

    assert resumed.status == GraphStatus.COMPLETE
    assert resumed.trip_request is not None
    assert resumed.trip_request.destination == "Dubai"
    assert resumed.trip_request.travelers == 2
    assert resumed.trip_request.duration_days == 5
    assert resumed.trip_request.budget_amount == Decimal("150000")
    assert resumed.trip_request.departure_city == "Mumbai"


def test_graph_checkpoint_allows_state_lookup(
    agent_service: TripPlannerAgentService,
) -> None:
    thread_id = "checkpoint-thread"
    agent_service.start(INCOMPLETE_REQUEST, thread_id=thread_id)

    checkpointed = agent_service.get_state(thread_id)

    assert checkpointed is not None
    assert checkpointed.status == GraphStatus.AWAITING_USER
    assert checkpointed.trip_request is not None
    assert checkpointed.trip_request.destination == "Dubai"


def test_graph_is_integration_testable_end_to_end(
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
    from langchain_core.runnables import RunnableConfig

    graph = compile_trip_planner_graph(
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
    config: RunnableConfig = {"configurable": {"thread_id": "integration-thread"}}
    result = graph.invoke({"user_request": COMPLETE_REQUEST}, config=config)

    assert result["status"] == GraphStatus.COMPLETE.value
    assert result["trip_request"] is not None
