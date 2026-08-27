"""Merge and engine tests for selective modifications."""

from __future__ import annotations

from decimal import Decimal

from app.itinerary.schemas import Itinerary, ItineraryDay, ItineraryItemCategory
from app.modification.engine import ModificationEngine
from app.modification.merger import merge_modified_itinerary
from app.modification.schemas import (
    ModificationIntent,
    ModificationScope,
    TripModificationRequest,
)
from app.modification.scope import resolve_modification_scope

from tests.itinerary.fixtures import (
    example_itinerary_context,
    example_valid_itinerary,
    fast_assumptions,
)


def _restaurant_source(day: ItineraryDay) -> str | None:
    if day.meal is not None:
        return day.meal.item.source_id
    for item in day.items:
        if item.category == ItineraryItemCategory.RESTAURANT:
            return item.source_id
    return None


def _attraction_sources(day: ItineraryDay) -> list[str]:
    return [
        item.source_id
        for item in day.items
        if item.category == ItineraryItemCategory.ATTRACTION and item.source_id
    ]


def _hotel_source(itinerary: Itinerary) -> str | None:
    for item in itinerary.infrastructure_items:
        if item.category == ItineraryItemCategory.HOTEL:
            return item.source_id
    return None


def _engine() -> ModificationEngine:
    return ModificationEngine(assumptions=fast_assumptions())


def test_merge_preserves_unaffected_days() -> None:
    itinerary = example_valid_itinerary(duration_days=3)
    unchanged_day = itinerary.days[0]
    modified_day = itinerary.days[1].model_copy(
        update={"subtotal": itinerary.days[1].subtotal + Decimal("1")}
    )
    scope = ModificationScope(affected_days=[2])

    merged = merge_modified_itinerary(
        previous=itinerary,
        modified_days=[modified_day],
        scope=scope,
    )

    assert merged.days[0] == unchanged_day
    assert merged.days[2] == itinerary.days[2]
    assert merged.days[1].subtotal == modified_day.subtotal


def test_merge_preserves_item_ids_for_unchanged_sources() -> None:
    itinerary = example_valid_itinerary(duration_days=1)
    original_item = itinerary.days[0].items[0]
    modified_item = original_item.model_copy(
        update={
            "start_time": original_item.start_time,
            "end_time": original_item.end_time,
        }
    )
    modified_day = itinerary.days[0].model_copy(update={"items": [modified_item]})
    scope = ModificationScope(affected_days=[1])

    merged = merge_modified_itinerary(
        previous=itinerary,
        modified_days=[modified_day],
        scope=scope,
    )

    assert merged.days[0].items[0].item_id == original_item.item_id
    assert merged.days[0].items[0].source_id == original_item.source_id


def test_pace_modification_changes_day_two_content() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_PACE,
        target_days=[2],
        requested_changes=["more relaxed"],
        raw_message="Make day 2 more relaxed.",
    )
    scope = ModificationScope(
        affected_days=[2],
        requires_budget_recompute=True,
        requires_critic=True,
    )
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert result.itinerary.days[0] == previous.days[0]
    assert result.itinerary.days[2] == previous.days[2]
    after_day = result.itinerary.days[1]
    before_day = previous.days[1]
    assert after_day != before_day
    assert len(_attraction_sources(after_day)) <= len(_attraction_sources(before_day))
    assert any(
        item.category == ItineraryItemCategory.FREE_TIME for item in after_day.items
    )
    assert after_day.items[0].start_time >= before_day.items[0].start_time


def test_restaurant_modification_changes_source_id() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    before_source = _restaurant_source(previous.days[2])
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_RESTAURANT,
        target_days=[3],
        requested_changes=["cheaper dinner"],
        raw_message="Find a cheaper dinner on day 3.",
    )
    scope = ModificationScope(
        affected_days=[3],
        requires_tool_refresh=True,
        requires_budget_recompute=True,
        requires_critic=True,
    )
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert result.itinerary.days[0] == previous.days[0]
    assert result.itinerary.days[1] == previous.days[1]
    after_source = _restaurant_source(result.itinerary.days[2])
    assert after_source is not None
    assert after_source != before_source


def test_reduce_cost_changes_cost_bearing_choices() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.REDUCE_COST,
        requested_changes=["more budget friendly"],
        raw_message="Make the trip more budget friendly.",
    )
    scope = resolve_modification_scope(request, itinerary=previous)
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert scope.affected_days == [1, 2, 3]
    changed_restaurants = [
        _restaurant_source(after) != _restaurant_source(before)
        for before, after in zip(previous.days, result.itinerary.days, strict=True)
    ]
    changed_attractions = [
        _attraction_sources(after) != _attraction_sources(before)
        for before, after in zip(previous.days, result.itinerary.days, strict=True)
    ]
    assert any(changed_restaurants) or any(changed_attractions)
    assert result.itinerary.total_estimated_cost <= previous.total_estimated_cost


def test_reduce_cost_preserves_existing_relaxed_day() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    paced = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=TripModificationRequest(
            intent=ModificationIntent.CHANGE_PACE,
            target_days=[2],
            requested_changes=["more relaxed"],
            raw_message="Make day 2 more relaxed.",
        ),
        scope=ModificationScope(
            affected_days=[2],
            requires_budget_recompute=True,
            requires_critic=True,
        ),
    )
    assert paced.itinerary is not None
    request = TripModificationRequest(
        intent=ModificationIntent.REDUCE_COST,
        requested_changes=["more budget friendly"],
        raw_message="Make the trip more budget friendly.",
    )
    result = _engine().apply(
        previous_itinerary=paced.itinerary,
        context=context,
        modification=request,
        scope=resolve_modification_scope(request, itinerary=paced.itinerary),
    )
    assert result.success is True
    assert result.itinerary is not None
    assert any(
        item.category == ItineraryItemCategory.FREE_TIME
        for item in result.itinerary.days[1].items
    )


def test_change_hotel_uses_a_different_grounded_hotel() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    before_hotel = _hotel_source(previous)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_HOTEL,
        requested_changes=["cheaper hotel"],
        raw_message="Change the hotel.",
    )
    scope = resolve_modification_scope(request, itinerary=previous)
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    after_hotel = _hotel_source(result.itinerary)
    assert before_hotel is not None
    assert after_hotel is not None
    assert after_hotel != before_hotel
    assert result.itinerary.days == previous.days


def test_change_hotel_is_infeasible_when_only_one_offer() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    current_hotel = _hotel_source(previous)
    assert current_hotel is not None
    assert context.hotel_search is not None
    matching = [
        hotel
        for hotel in context.hotel_search.hotels
        if hotel.hotel_id == current_hotel
    ]
    assert matching
    context = context.model_copy(
        update={
            "hotel_search": context.hotel_search.model_copy(update={"hotels": matching})
        }
    )
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_HOTEL,
        requested_changes=["change hotel"],
        raw_message="Change the hotel.",
    )
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=resolve_modification_scope(request, itinerary=previous),
    )

    assert result.success is False
    assert result.itinerary is None
    assert result.error_message is not None
    assert "alternative hotels" in result.error_message.lower()


def test_preference_modification_changes_grounded_attractions() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_PREFERENCE,
        requested_changes=["more culture", "less shopping"],
        raw_message="We want more culture and less shopping.",
    )
    scope = resolve_modification_scope(request, itinerary=previous)
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert scope.affected_days == [1, 2, 3]
    before_sources = [
        source for day in previous.days for source in _attraction_sources(day)
    ]
    after_sources = [
        source for day in result.itinerary.days for source in _attraction_sources(day)
    ]
    assert after_sources != before_sources
    assert "places/mall" not in after_sources


def test_change_activity_excludes_current_source() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    before = _attraction_sources(previous.days[1])
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_ACTIVITY,
        target_days=[2],
        requested_changes=["replace activity"],
        raw_message="Replace the most expensive activity.",
    )
    scope = ModificationScope(affected_days=[2], requires_critic=True)
    result = _engine().apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    after = _attraction_sources(result.itinerary.days[1])
    assert after
    assert after != before
    assert result.itinerary.days[0] == previous.days[0]


def test_budget_recompute_uses_deterministic_engine() -> None:
    context = example_itinerary_context(duration_days=2)
    itinerary = example_valid_itinerary(duration_days=2)
    recomputed = _engine().recompute_budget(context=context, itinerary=itinerary)
    assert recomputed.currency == context.budget_result.currency
    assert recomputed.budget_amount == context.budget_result.budget_amount
