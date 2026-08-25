"""Unit tests for modification extraction and scope."""

from __future__ import annotations

from app.modification.schemas import ModificationIntent, TripModificationRequest
from app.modification.scope import build_refresh_plan, resolve_modification_scope

from tests.fakes.modification_stub import extract_modification_from_text
from tests.itinerary.fixtures import example_valid_itinerary


def test_extract_modify_day_intent() -> None:
    request = extract_modification_from_text("Make day 2 more relaxed.")
    assert request.intent == ModificationIntent.CHANGE_PACE
    assert request.target_days == [2]


def test_extract_change_hotel_intent() -> None:
    request = extract_modification_from_text("Find a cheaper hotel.")
    assert request.intent == ModificationIntent.CHANGE_HOTEL


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
