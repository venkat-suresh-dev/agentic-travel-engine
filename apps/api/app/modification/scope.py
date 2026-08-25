"""Deterministic modification scope resolution."""

from __future__ import annotations

from app.itinerary.schemas import Itinerary, ItineraryItemCategory
from app.modification.schemas import (
    ModificationIntent,
    ModificationScope,
    RefreshPlan,
    TripModificationRequest,
)


def resolve_modification_scope(
    request: TripModificationRequest,
    *,
    itinerary: Itinerary,
) -> ModificationScope:
    """Map a structured modification request to affected scope."""
    affected_days = sorted(set(request.target_days))
    affected_item_ids = list(request.target_item_ids)

    if not affected_days and request.intent in {
        ModificationIntent.CHANGE_HOTEL,
        ModificationIntent.MODIFY_TRIP_REQUIREMENT,
    }:
        affected_days = []

    if not affected_days and request.intent not in {
        ModificationIntent.CHANGE_HOTEL,
        ModificationIntent.MODIFY_TRIP_REQUIREMENT,
    }:
        affected_days = _infer_days_from_items(itinerary, affected_item_ids)

    if not affected_days and request.intent in {
        ModificationIntent.CHANGE_PACE,
        ModificationIntent.MODIFY_DAY,
        ModificationIntent.REDUCE_COST,
        ModificationIntent.CHANGE_RESTAURANT,
        ModificationIntent.CHANGE_ACTIVITY,
        ModificationIntent.REPLACE_ITEM,
    }:
        affected_days = _infer_days_from_message(itinerary, request)

    if not affected_item_ids and affected_days:
        affected_item_ids = _items_for_days(itinerary, affected_days, request.intent)

    affected_trip_fields = _affected_trip_fields(request.intent)
    requires_tool_refresh = _requires_tool_refresh(request.intent)
    requires_budget_recompute = _requires_budget_recompute(request.intent)
    requires_critic = True

    return ModificationScope(
        affected_days=affected_days,
        affected_item_ids=affected_item_ids,
        affected_trip_fields=affected_trip_fields,
        requires_tool_refresh=requires_tool_refresh,
        requires_budget_recompute=requires_budget_recompute,
        requires_critic=requires_critic,
    )


def build_refresh_plan(
    request: TripModificationRequest,
    scope: ModificationScope,
) -> RefreshPlan:
    """Map modification scope to the smallest necessary provider refresh."""
    if not scope.requires_tool_refresh:
        return RefreshPlan()

    intent = request.intent
    if intent == ModificationIntent.MODIFY_TRIP_REQUIREMENT:
        return RefreshPlan(
            refresh_weather=True,
            refresh_flights=True,
            refresh_hotels=True,
            refresh_places=True,
            refresh_distance=True,
            refresh_currency=True,
            refresh_rag=True,
        )

    if intent == ModificationIntent.CHANGE_HOTEL:
        return RefreshPlan(
            refresh_hotels=True,
            refresh_currency=True,
            refresh_distance=True,
        )

    if intent in {
        ModificationIntent.CHANGE_RESTAURANT,
        ModificationIntent.REDUCE_COST,
    }:
        return RefreshPlan(refresh_places=True)

    if intent == ModificationIntent.CHANGE_ACTIVITY:
        return RefreshPlan(refresh_places=True, refresh_distance=True)

    if intent == ModificationIntent.REPLACE_ITEM:
        return RefreshPlan(refresh_places=True, refresh_distance=True)

    return RefreshPlan()


def _infer_days_from_items(itinerary: Itinerary, item_ids: list[str]) -> list[int]:
    days: set[int] = set()
    for day in itinerary.days:
        for item in day.items:
            if item.item_id in item_ids:
                days.add(day.day_number)
    return sorted(days)


def _infer_days_from_message(
    itinerary: Itinerary,
    request: TripModificationRequest,
) -> list[int]:
    lowered = request.raw_message.lower()
    for day in itinerary.days:
        if f"day {day.day_number}" in lowered:
            return [day.day_number]
    return []


def _items_for_days(
    itinerary: Itinerary,
    day_numbers: list[int],
    intent: ModificationIntent,
) -> list[str]:
    item_ids: list[str] = []
    for day in itinerary.days:
        if day.day_number not in day_numbers:
            continue
        for item in day.items:
            if intent == ModificationIntent.CHANGE_RESTAURANT:
                if item.category == ItineraryItemCategory.RESTAURANT:
                    item_ids.append(item.item_id)
            elif intent == ModificationIntent.CHANGE_ACTIVITY:
                if item.category == ItineraryItemCategory.ATTRACTION:
                    item_ids.append(item.item_id)
            elif intent in {
                ModificationIntent.REDUCE_COST,
                ModificationIntent.REPLACE_ITEM,
            }:
                item_ids.append(item.item_id)
            elif intent == ModificationIntent.CHANGE_PACE:
                if item.category == ItineraryItemCategory.ATTRACTION:
                    item_ids.append(item.item_id)
            else:
                item_ids.append(item.item_id)
    return item_ids


def _affected_trip_fields(intent: ModificationIntent) -> list[str]:
    if intent == ModificationIntent.MODIFY_TRIP_REQUIREMENT:
        return ["start_date", "duration_days", "budget_amount", "destination"]
    if intent == ModificationIntent.CHANGE_HOTEL:
        return ["hotel"]
    return []


def _requires_tool_refresh(intent: ModificationIntent) -> bool:
    return intent in {
        ModificationIntent.CHANGE_HOTEL,
        ModificationIntent.CHANGE_RESTAURANT,
        ModificationIntent.CHANGE_ACTIVITY,
        ModificationIntent.REPLACE_ITEM,
        ModificationIntent.MODIFY_TRIP_REQUIREMENT,
        ModificationIntent.REDUCE_COST,
    }


def _requires_budget_recompute(intent: ModificationIntent) -> bool:
    return intent in {
        ModificationIntent.CHANGE_HOTEL,
        ModificationIntent.CHANGE_RESTAURANT,
        ModificationIntent.CHANGE_ACTIVITY,
        ModificationIntent.REPLACE_ITEM,
        ModificationIntent.REDUCE_COST,
        ModificationIntent.MODIFY_TRIP_REQUIREMENT,
        ModificationIntent.CHANGE_PACE,
        ModificationIntent.MODIFY_DAY,
    }
