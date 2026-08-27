"""Compute factual itinerary diffs for modification responses."""

from __future__ import annotations

from app.itinerary.schemas import (
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
)


def changed_item_ids(previous: Itinerary, current: Itinerary) -> list[str]:
    previous_items = _items_by_id(previous)
    current_items = _items_by_id(current)
    changed: list[str] = []
    for item_id, current_item in current_items.items():
        previous_item = previous_items.get(item_id)
        if previous_item is None:
            changed.append(item_id)
            continue
        if (
            previous_item.source_id != current_item.source_id
            or previous_item.title != current_item.title
            or previous_item.start_time != current_item.start_time
            or previous_item.end_time != current_item.end_time
        ):
            changed.append(item_id)
    return changed


def change_facts(
    previous: Itinerary, current: Itinerary, *, affected_days: list[int]
) -> list[str]:
    facts: list[str] = []
    for day_number in affected_days:
        previous_day = _day(previous, day_number)
        current_day = _day(current, day_number)
        if previous_day is None or current_day is None:
            continue
        previous_count = _activity_count(previous_day)
        current_count = _activity_count(current_day)
        if previous_count != current_count:
            facts.append(f"{previous_count} activities → {current_count}")
        previous_travel = sum(leg.duration_seconds for leg in previous_day.travel_legs)
        current_travel = sum(leg.duration_seconds for leg in current_day.travel_legs)
        delta_minutes = round((previous_travel - current_travel) / 60)
        if delta_minutes > 0:
            facts.append(f"Travel time ↓ {delta_minutes} min")
        elif delta_minutes < 0:
            facts.append(f"Travel time ↑ {abs(delta_minutes)} min")
        if _day_sources(current_day) != _day_sources(previous_day):
            facts.append(f"Day {day_number} places updated")

    budget_delta = current.budget_total_cost - previous.budget_total_cost
    if budget_delta != 0:
        direction = "decreased" if budget_delta < 0 else "increased"
        facts.append(
            f"Budget {direction} by {current.budget_currency} {abs(budget_delta)}"
        )

    if _hotel_id(previous) == _hotel_id(current):
        facts.append("Hotel unchanged")
    else:
        facts.append("Hotel updated")
    if _flight_id(previous) == _flight_id(current):
        facts.append("Flights unchanged")
    return facts


def _items_by_id(itinerary: Itinerary) -> dict[str, ItineraryItem]:
    items: dict[str, ItineraryItem] = {}
    for day in itinerary.days:
        for item in day.items:
            items[item.item_id] = item
    for item in itinerary.infrastructure_items:
        items[item.item_id] = item
    return items


def _day(itinerary: Itinerary, day_number: int) -> ItineraryDay | None:
    return next((day for day in itinerary.days if day.day_number == day_number), None)


def _activity_count(day: ItineraryDay) -> int:
    return sum(
        1
        for item in day.items
        if item.category
        in {ItineraryItemCategory.ATTRACTION, ItineraryItemCategory.FREE_TIME}
    )


def _day_sources(day: ItineraryDay) -> set[str]:
    return {item.source_id for item in day.items if item.source_id}


def _hotel_id(itinerary: Itinerary) -> str | None:
    for item in itinerary.infrastructure_items:
        if item.category == ItineraryItemCategory.HOTEL:
            return item.source_id
    return None


def _flight_id(itinerary: Itinerary) -> str | None:
    for item in itinerary.infrastructure_items:
        if item.category == ItineraryItemCategory.FLIGHT:
            return item.source_id
    return None
