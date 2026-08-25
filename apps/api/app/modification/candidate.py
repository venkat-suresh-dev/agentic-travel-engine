"""Bridge itinerary and selection candidates for modification."""

from __future__ import annotations

from app.itinerary.schemas import (
    CandidateDayPlan,
    Itinerary,
    ItineraryDay,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
)


def candidate_from_itinerary(itinerary: Itinerary) -> ItinerarySelectionCandidate:
    """Derive a grounded selection candidate from an approved itinerary."""
    days: list[CandidateDayPlan] = []
    for day in itinerary.days:
        attraction_ids = [
            item.source_id
            for item in day.items
            if item.category == ItineraryItemCategory.ATTRACTION and item.source_id
        ]
        restaurant_id = _restaurant_source_id(day)
        days.append(
            CandidateDayPlan(
                day_number=day.day_number,
                attraction_source_ids=attraction_ids,
                restaurant_source_id=restaurant_id,
            )
        )
    return ItinerarySelectionCandidate(days=days)


def _restaurant_source_id(day: ItineraryDay) -> str:
    if day.meal is not None and day.meal.item.source_id:
        return day.meal.item.source_id
    for item in day.items:
        if item.category == ItineraryItemCategory.RESTAURANT and item.source_id:
            return item.source_id
    msg = f"day {day.day_number} has no restaurant source"
    raise ValueError(msg)
