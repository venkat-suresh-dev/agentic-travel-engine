"""Tests for LLM extraction and adapter behavior."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TypeVar

import pytest
from app.agent.exceptions import RequirementExtractionError
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.service import TripPlannerAgentService
from app.agent.state import AgentState, GraphStatus
from app.domain.trip_request import TripRequest
from app.llm.anthropic import AnthropicLLMAdapter
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.weather import WeatherTool
from pydantic import BaseModel

from tests.fakes.extract_stub import extract_from_text
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter

T = TypeVar("T", bound=BaseModel)

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)
INCOMPLETE_REQUEST = "Plan a 5-day trip to Dubai for 2 people."
PREFERENCES_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people. We prefer a relaxed pace and good food."
)


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
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
        llm_adapter=fake_adapter,
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
    )


def test_fully_specified_trip_request(fake_adapter: FakeLLMAdapter) -> None:
    result = fake_adapter.generate_structured(
        system_prompt="system",
        user_prompt=(
            "Extract structured trip requirements from this user request:\n"
            f"{COMPLETE_REQUEST}"
        ),
        response_model=TripRequest,
    )

    assert result.data.destination == "Dubai"
    assert result.data.travelers == 2
    assert result.data.budget_amount == Decimal("150000")
    assert result.data.departure_city == "Mumbai"


def test_partially_specified_trip_request(fake_adapter: FakeLLMAdapter) -> None:
    result = fake_adapter.generate_structured(
        system_prompt="system",
        user_prompt=(
            "Extract structured trip requirements from this user request:\n"
            f"{INCOMPLETE_REQUEST}"
        ),
        response_model=TripRequest,
    )

    assert result.data.destination == "Dubai"
    assert result.data.budget_amount is None
    assert result.data.departure_city is None


def test_missing_budget(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a 5-day trip to Dubai for 2 people departing from Mumbai.",
        thread_id="llm-missing-budget",
    )

    assert result.validation is not None
    assert "budget_amount" in result.validation.missing_fields


def test_missing_dates(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a trip to Dubai for 2 people under ₹1,50,000 departing from Mumbai.",
        thread_id="llm-missing-dates",
    )

    assert result.validation is not None
    assert "duration_days" in result.validation.missing_fields


def test_missing_destination(agent_service: TripPlannerAgentService) -> None:
    result = agent_service.start(
        "Plan a 5-day trip for 2 people under ₹1,50,000 departing from Mumbai.",
        thread_id="llm-missing-destination",
    )

    assert result.validation is not None
    assert "destination" in result.validation.missing_fields


def test_explicit_traveler_count(fake_adapter: FakeLLMAdapter) -> None:
    result = fake_adapter.generate_structured(
        system_prompt="system",
        user_prompt=(
            "Extract structured trip requirements from this user request:\n"
            "Plan a trip to Dubai for 4 travelers."
        ),
        response_model=TripRequest,
    )

    assert result.data.travelers == 4


def test_explicit_departure_city(fake_adapter: FakeLLMAdapter) -> None:
    result = fake_adapter.generate_structured(
        system_prompt="system",
        user_prompt=(
            "Extract structured trip requirements from this user request:\n"
            "Plan a trip to Dubai departing from Mumbai."
        ),
        response_model=TripRequest,
    )

    assert result.data.departure_city == "Mumbai"


def test_explicit_preferences(fake_adapter: FakeLLMAdapter) -> None:
    result = fake_adapter.generate_structured(
        system_prompt="system",
        user_prompt=(
            "Extract structured trip requirements from this user request:\n"
            f"{PREFERENCES_REQUEST}"
        ),
        response_model=TripRequest,
    )

    assert "relaxed pace" in result.data.preferences[0].lower()


def test_fully_specified_request_with_dates() -> None:
    adapter = FakeLLMAdapter(
        extractor=lambda _system, _user, _model: TripRequest(
            destination="Dubai",
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 16),
            duration_days=5,
            travelers=2,
            budget_amount=Decimal("150000"),
            departure_city="Mumbai",
            preferences=["relaxed pace", "good food"],
        )
    )

    result = adapter.generate_structured(
        system_prompt="system",
        user_prompt="ignored",
        response_model=TripRequest,
    )

    assert result.data.start_date == date(2026, 10, 12)
    assert result.data.end_date == date(2026, 10, 16)
    assert result.data.preferences == ["relaxed pace", "good food"]


def test_malformed_provider_output_rejected() -> None:
    adapter = FakeLLMAdapter(
        malformed_payload={
            "destination": "Dubai",
            "duration_days": 0,
            "travelers": 2,
        }
    )

    with pytest.raises(LLMStructuredOutputError):
        adapter.generate_structured(
            system_prompt="system",
            user_prompt="request",
            response_model=TripRequest,
        )


def test_provider_failure_is_controlled() -> None:
    adapter = FakeLLMAdapter(should_fail=True)
    extract_node = build_extract_requirements_node(adapter)
    state: AgentState = {"user_request": COMPLETE_REQUEST, "messages": []}

    with pytest.raises(RequirementExtractionError):
        extract_node(state)


def test_adapter_replacement_with_custom_extractor() -> None:
    def custom_extractor(
        _system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        assert response_model is TripRequest
        return TripRequest(destination="Tokyo", travelers=1)  # type: ignore[return-value]

    adapter = FakeLLMAdapter(extractor=custom_extractor)
    result = adapter.generate_structured(
        system_prompt="system",
        user_prompt="Plan a solo trip to Tokyo",
        response_model=TripRequest,
    )

    assert result.data.destination == "Tokyo"
    assert result.data.travelers == 1


def test_malformed_output_cannot_enter_graph_state(
    fake_adapter: FakeLLMAdapter,
) -> None:
    failing_adapter = FakeLLMAdapter(
        malformed_payload={
            "destination": "Dubai",
            "start_date": "2026-12-10",
            "end_date": "2026-12-01",
        }
    )
    extract_node = build_extract_requirements_node(failing_adapter)
    state: AgentState = {"user_request": INCOMPLETE_REQUEST, "messages": []}

    with pytest.raises(RequirementExtractionError):
        extract_node(state)

    assert state.get("trip_request") is None


def test_llm_failure_does_not_invent_values_on_resume(
    fake_adapter: FakeLLMAdapter,
) -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    checkpointer = InMemorySaver()
    service = TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=checkpointer,
    )
    thread_id = "llm-resume-failure"
    service.start(INCOMPLETE_REQUEST, thread_id=thread_id)

    failing_service = TripPlannerAgentService(
        llm_adapter=FakeLLMAdapter(should_fail=True),
        checkpointer=checkpointer,
    )

    with pytest.raises(RequirementExtractionError):
        failing_service.resume(thread_id, "Budget is ₹1,50,000")

    checkpointed = service.get_state(thread_id)
    assert checkpointed is not None
    assert checkpointed.trip_request is not None
    assert checkpointed.trip_request.budget_amount is None


def test_extract_from_text_still_does_not_invent_missing_values() -> None:
    trip_request = extract_from_text(INCOMPLETE_REQUEST)

    assert trip_request.destination == "Dubai"
    assert trip_request.budget_amount is None


def test_anthropic_adapter_requires_api_key() -> None:
    from app.core.config import Settings

    settings = Settings(anthropic_api_key="")
    with pytest.raises(LLMProviderError):
        AnthropicLLMAdapter(settings)


def test_anthropic_adapter_rejects_missing_parsed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.core.config import Settings

    class FakeMessages:
        def parse(self, **_kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                parsed_output=None,
                usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            )

    class FakeClient:
        messages = FakeMessages()

    settings = Settings(anthropic_api_key="test-key")
    adapter = AnthropicLLMAdapter(settings)
    monkeypatch.setattr(adapter, "_client", FakeClient())

    with pytest.raises(LLMStructuredOutputError):
        adapter.generate_structured(
            system_prompt="system",
            user_prompt="request",
            response_model=TripRequest,
        )


def test_anthropic_adapter_wraps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import anthropic
    import httpx2
    from app.core.config import Settings

    class FakeMessages:
        def parse(self, **_kwargs: object) -> TripRequest:
            raise anthropic.APIError(
                message="provider down",
                request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"),
                body=None,
            )

    class FakeClient:
        messages = FakeMessages()

    settings = Settings(anthropic_api_key="test-key")
    adapter = AnthropicLLMAdapter(settings)
    monkeypatch.setattr(adapter, "_client", FakeClient())

    with pytest.raises(LLMProviderError):
        adapter.generate_structured(
            system_prompt="system",
            user_prompt="request",
            response_model=TripRequest,
        )


def test_graph_complete_flow_with_fake_adapter(
    agent_service: TripPlannerAgentService,
) -> None:
    result = agent_service.start(COMPLETE_REQUEST, thread_id="llm-complete")

    assert result.status == GraphStatus.COMPLETE
    assert result.trip_request is not None
    assert result.trip_request.destination == "Dubai"
    assert result.weather_forecast is not None
    assert result.weather_tool_metadata is not None
    assert result.flight_search is not None
    assert result.flight_tool_metadata is not None
