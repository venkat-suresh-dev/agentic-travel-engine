"""Unit tests for modification extraction and scope."""

from __future__ import annotations

from typing import TypeVar

from app.agent.nodes.extract_modification import build_extract_modification_node
from app.llm.exceptions import LLMProviderError
from app.llm.types import StructuredLLMResult
from app.modification.schemas import ModificationIntent, TripModificationRequest
from app.modification.scope import build_refresh_plan, resolve_modification_scope
from pydantic import BaseModel

from tests.fakes.modification_stub import extract_modification_from_text
from tests.itinerary.fixtures import example_valid_itinerary

T = TypeVar("T", bound=BaseModel)


class _FailingLLM:
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        raise LLMProviderError("Groq request failed with status 429")


def test_extract_modify_day_intent() -> None:
    request = extract_modification_from_text("Make day 2 more relaxed.")
    assert request.intent == ModificationIntent.CHANGE_PACE
    assert request.target_days == [2]


def test_extract_slower_day_intent() -> None:
    request = extract_modification_from_text("Make Day 2 slower")
    assert request.intent == ModificationIntent.CHANGE_PACE
    assert request.target_days == [2]


def test_extract_reduce_travel_intent() -> None:
    request = extract_modification_from_text("Reduce travel on Day 3")
    assert request.intent == ModificationIntent.CHANGE_PACE
    assert request.target_days == [3]


def test_extract_change_hotel_intent() -> None:
    request = extract_modification_from_text("Find a cheaper hotel.")
    assert request.intent == ModificationIntent.CHANGE_HOTEL


def test_extract_lower_trip_cost_intent() -> None:
    request = extract_modification_from_text("Lower the trip cost")
    assert request.intent == ModificationIntent.REDUCE_COST


def test_extract_change_restaurant_intent() -> None:
    request = extract_modification_from_text("Make dinner on day 3 cheaper.")
    assert request.intent == ModificationIntent.CHANGE_RESTAURANT
    assert request.target_days == [3]


def test_scope_pace_change_does_not_refresh_providers() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_PACE,
        target_days=[2],
        requested_changes=["more relaxed"],
        raw_message="Make day 2 more relaxed.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    plan = build_refresh_plan(request, scope)

    assert scope.affected_days == [2]
    assert scope.requires_tool_refresh is False
    assert plan.requires_any_refresh is False


def test_scope_hotel_change_refreshes_hotels() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_HOTEL,
        requested_changes=["cheaper hotel"],
        raw_message="Find a cheaper hotel.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    plan = build_refresh_plan(request, scope)

    assert scope.requires_tool_refresh is True
    assert plan.refresh_hotels is True
    assert plan.refresh_weather is False


def test_scope_date_change_refreshes_time_sensitive_tools() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.MODIFY_TRIP_REQUIREMENT,
        requested_changes=["move to november"],
        raw_message="Move the trip to November 10-14.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    plan = build_refresh_plan(request, scope)

    assert plan.refresh_weather is True
    assert plan.refresh_flights is True
    assert plan.refresh_hotels is True


def test_scope_reduce_cost_without_day_targets_whole_trip() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.REDUCE_COST,
        requested_changes=["budget friendly"],
        raw_message="Make the trip more budget friendly.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    assert scope.affected_days == [1, 2, 3]
    assert "hotel" in scope.affected_trip_fields


def test_scope_preference_targets_all_days() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_PREFERENCE,
        requested_changes=["more culture"],
        raw_message="We want more culture and less shopping.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    assert scope.affected_days == [1, 2, 3]


def test_scope_restaurant_change_refreshes_places_only() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_RESTAURANT,
        target_days=[3],
        requested_changes=["cheaper dinner"],
        raw_message="Make dinner on day 3 cheaper.",
    )
    scope = resolve_modification_scope(request, itinerary=itinerary)
    plan = build_refresh_plan(request, scope)

    assert scope.affected_days == [3]
    assert plan.refresh_places is True
    assert plan.refresh_hotels is False
    assert plan.refresh_weather is False


def test_extract_preference_intent() -> None:
    request = extract_modification_from_text("We want more culture and less shopping.")
    assert request.intent == ModificationIntent.CHANGE_PREFERENCE


def test_extract_modification_falls_back_when_llm_unavailable() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    node = build_extract_modification_node(_FailingLLM())
    result = node(
        {
            "user_clarification": "Make day 2 more relaxed.",
            "itinerary": itinerary.model_dump(mode="json"),
            "messages": [],
        }
    )
    modification = result["modification_request"]
    assert isinstance(modification, dict)
    assert modification["intent"] == ModificationIntent.CHANGE_PACE.value
    assert modification["target_days"] == [2]
