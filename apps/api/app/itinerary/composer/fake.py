"""Deterministic fake itinerary composer for offline tests."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.clustering import select_weather_aware_attractions
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.critic.schemas import CriticIssue, CriticIssueCode
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate


class FakeItineraryComposer:
    """Select grounded attractions/restaurants deterministically."""

    def __init__(self, assumptions: SchedulingAssumptions | None = None) -> None:
        self._assumptions = assumptions or SchedulingAssumptions()

    def compose(
        self,
        *,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
    ) -> ItinerarySelectionCandidate:
        duration = context.trip_request.duration_days or 1
        attraction_ids = catalog.attraction_ids()
        restaurant_ids = catalog.restaurant_ids()
        if not restaurant_ids:
            raise ValueError("at least one grounded restaurant is required")

        feedback_by_day = _feedback_by_day(context)
        days: list[CandidateDayPlan] = []
        for day_number in range(1, duration + 1):
            day_feedback = feedback_by_day.get(day_number, [])
            selected_attractions = select_weather_aware_attractions(
                attraction_ids,
                day_number=day_number,
                catalog=catalog,
                assumptions=self._assumptions,
                max_items=1,
            )
            if _needs_indoor(day_feedback):
                indoor_ids = [
                    attraction_id
                    for attraction_id in attraction_ids
                    if catalog.attractions[attraction_id].is_indoor
                ]
                if indoor_ids:
                    selected_attractions = [indoor_ids[0]]

            if not selected_attractions and attraction_ids:
                selected_attractions = [
                    attraction_ids[(day_number - 1) % len(attraction_ids)]
                ]

            restaurant_id = restaurant_ids[(day_number - 1) % len(restaurant_ids)]
            if any(
                issue.code == CriticIssueCode.MISSING_MEAL for issue in day_feedback
            ):
                restaurant_id = restaurant_ids[0]

            days.append(
                CandidateDayPlan(
                    day_number=day_number,
                    attraction_source_ids=selected_attractions,
                    restaurant_source_id=restaurant_id,
                )
            )
        return ItinerarySelectionCandidate(days=days)


def _feedback_by_day(context: ItineraryBuildContext) -> dict[int, list[CriticIssue]]:
    grouped: dict[int, list[CriticIssue]] = {}
    for issue in context.critic_feedback:
        if issue.day_number is None:
            continue
        grouped.setdefault(issue.day_number, []).append(issue)
    return grouped


def _needs_indoor(day_feedback: list[CriticIssue]) -> bool:
    return any(
        issue.code == CriticIssueCode.WEATHER_RULE_VIOLATION for issue in day_feedback
    )
