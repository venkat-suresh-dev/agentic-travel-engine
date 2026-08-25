"""Deterministic fake itinerary composer for offline tests."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.clustering import select_weather_aware_attractions
from app.itinerary.context import ItineraryBuildContext
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

        days: list[CandidateDayPlan] = []
        for day_number in range(1, duration + 1):
            selected_attractions = select_weather_aware_attractions(
                attraction_ids,
                day_number=day_number,
                catalog=catalog,
                assumptions=self._assumptions,
                max_items=1,
            )
            if not selected_attractions and attraction_ids:
                selected_attractions = [
                    attraction_ids[(day_number - 1) % len(attraction_ids)]
                ]
            restaurant_id = restaurant_ids[(day_number - 1) % len(restaurant_ids)]
            days.append(
                CandidateDayPlan(
                    day_number=day_number,
                    attraction_source_ids=selected_attractions,
                    restaurant_source_id=restaurant_id,
                )
            )
        return ItinerarySelectionCandidate(days=days)
