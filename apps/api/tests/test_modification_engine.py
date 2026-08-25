"""Merge and engine tests for selective modifications."""

from __future__ import annotations

from decimal import Decimal

from app.modification.engine import ModificationEngine
from app.modification.merger import merge_modified_itinerary
from app.modification.schemas import (
    ModificationIntent,
    ModificationScope,
    TripModificationRequest,
)

from tests.itinerary.fixtures import (
    example_itinerary_context,
    example_valid_itinerary,
)


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


def test_pace_modification_preserves_other_days() -> None:
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
    engine = ModificationEngine()
    result = engine.apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert result.itinerary.days[0] == previous.days[0]
    assert result.itinerary.days[2] == previous.days[2]


def test_restaurant_modification_changes_only_target_day() -> None:
    context = example_itinerary_context(duration_days=3)
    previous = example_valid_itinerary(duration_days=3)
    day_three_before = previous.days[2]
    request = TripModificationRequest(
        intent=ModificationIntent.CHANGE_RESTAURANT,
        target_days=[3],
        requested_changes=["cheaper dinner"],
        raw_message="Make dinner on day 3 cheaper.",
    )
    scope = ModificationScope(
        affected_days=[3],
        requires_tool_refresh=True,
        requires_budget_recompute=True,
        requires_critic=True,
    )
    engine = ModificationEngine()
    result = engine.apply(
        previous_itinerary=previous,
        context=context,
        modification=request,
        scope=scope,
    )

    assert result.success is True
    assert result.itinerary is not None
    assert result.itinerary.days[0] == previous.days[0]
    assert result.itinerary.days[1] == previous.days[1]
    assert result.itinerary.days[2] != day_three_before


def test_budget_recompute_uses_deterministic_engine() -> None:
    context = example_itinerary_context(duration_days=2)
    itinerary = example_valid_itinerary(duration_days=2)
    engine = ModificationEngine()
    recomputed = engine.recompute_budget(context=context, itinerary=itinerary)
    assert recomputed.currency == context.budget_result.currency
    assert recomputed.budget_amount == context.budget_result.budget_amount
