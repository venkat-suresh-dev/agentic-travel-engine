"""Deterministic merge of modified itinerary portions."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.itinerary.schemas import (
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
)
from app.modification.schemas import ModificationScope


def merge_modified_itinerary(
    *,
    previous: Itinerary,
    modified_days: list[ItineraryDay],
    scope: ModificationScope,
) -> Itinerary:
    """Merge modified days into the previous itinerary preserving stable IDs."""
    modified_by_day = {day.day_number: day for day in modified_days}
    merged_days: list[ItineraryDay] = []

    for previous_day in previous.days:
        if previous_day.day_number in scope.affected_days:
            merged_day = modified_by_day.get(previous_day.day_number)
            if merged_day is None:
                merged_days.append(previous_day)
                continue
            merged_days.append(
                _preserve_item_ids(previous_day=previous_day, modified_day=merged_day)
            )
        else:
            merged_days.append(previous_day)

    infrastructure = list(previous.infrastructure_items)
    if "hotel" in scope.affected_trip_fields:
        infrastructure = _replace_infrastructure(
            infrastructure,
            modified_days,
            category=ItineraryItemCategory.HOTEL,
        )

    total = _sum_days(merged_days)
    return previous.model_copy(
        update={
            "days": merged_days,
            "infrastructure_items": infrastructure,
            "total_estimated_cost": quantize_money(total),
        }
    )


def _preserve_item_ids(
    *,
    previous_day: ItineraryDay,
    modified_day: ItineraryDay,
) -> ItineraryDay:
    previous_by_source = {
        item.source_id: item.item_id
        for item in previous_day.items
        if item.source_id is not None
    }
    if modified_day.meal is not None and modified_day.meal.item.source_id:
        previous_meal_id = previous_by_source.get(modified_day.meal.item.source_id)
        if previous_meal_id is not None:
            meal_item = modified_day.meal.item.model_copy(
                update={"item_id": previous_meal_id}
            )
            modified_day = modified_day.model_copy(
                update={
                    "meal": modified_day.meal.model_copy(update={"item": meal_item})
                }
            )

    preserved_items: list[ItineraryItem] = []
    for item in modified_day.items:
        if item.source_id and item.source_id in previous_by_source:
            preserved_items.append(
                item.model_copy(update={"item_id": previous_by_source[item.source_id]})
            )
        else:
            preserved_items.append(item)

    return modified_day.model_copy(update={"items": preserved_items})


def _replace_infrastructure(
    infrastructure: list[ItineraryItem],
    modified_days: list[ItineraryDay],
    *,
    category: ItineraryItemCategory,
) -> list[ItineraryItem]:
    preserved = [item for item in infrastructure if item.category != category]
    new_items = [
        item for day in modified_days for item in day.items if item.category == category
    ]
    return preserved + new_items


def _sum_days(days: list[ItineraryDay]) -> Decimal:
    total = Decimal("0")
    for day in days:
        total += day.subtotal
    return total
