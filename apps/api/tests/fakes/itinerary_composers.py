"""Fake itinerary composers for critic retry tests."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate


class FlakyItineraryComposer(FakeItineraryComposer):
    """Fail composition for the first N attempts using invented sources."""

    def __init__(
        self,
        *,
        invalid_until_attempt: int = 1,
        assumptions: SchedulingAssumptions | None = None,
    ) -> None:
        super().__init__(assumptions=assumptions)
        self._invalid_until_attempt = invalid_until_attempt
        self.attempt_count = 0

    def compose(
        self,
        *,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
    ) -> ItinerarySelectionCandidate:
        self.attempt_count += 1
        if self.attempt_count <= self._invalid_until_attempt:
            duration = context.trip_request.duration_days or 1
            restaurant_ids = catalog.restaurant_ids()
            restaurant_id = restaurant_ids[0] if restaurant_ids else "places/invented"
            return ItinerarySelectionCandidate(
                days=[
                    CandidateDayPlan(
                        day_number=day_number,
                        attraction_source_ids=["places/invented-attraction"],
                        restaurant_source_id=restaurant_id,
                    )
                    for day_number in range(1, duration + 1)
                ]
            )
        return super().compose(context=context, catalog=catalog)
