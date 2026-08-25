"""Targeted itinerary composition for modifications."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.clustering import select_weather_aware_attractions
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate
from app.modification.candidate import candidate_from_itinerary
from app.modification.schemas import (
    ModificationIntent,
    ModificationScope,
    TripModificationRequest,
)


class ModificationComposer:
    """Compose only the itinerary portions affected by a modification."""

    def __init__(self, assumptions: SchedulingAssumptions | None = None) -> None:
        self._assumptions = assumptions or SchedulingAssumptions()

    def compose(
        self,
        *,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
        existing_candidate: ItinerarySelectionCandidate,
        modification: TripModificationRequest,
        scope: ModificationScope,
    ) -> ItinerarySelectionCandidate:
        if context.trip_request.duration_days is None:
            msg = "duration_days is required for modification composition"
            raise ValueError(msg)

        days = list(existing_candidate.days)
        for day_number in scope.affected_days:
            existing_day = next(
                (day for day in days if day.day_number == day_number),
                None,
            )
            if existing_day is None:
                continue
            days[day_number - 1] = self._compose_day(
                day_number=day_number,
                existing_day=existing_day,
                catalog=catalog,
                modification=modification,
                scope=scope,
            )

        if ModificationIntent.CHANGE_HOTEL in {modification.intent}:
            return existing_candidate

        return ItinerarySelectionCandidate(days=days)

    def _compose_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        catalog: GroundedCatalog,
        modification: TripModificationRequest,
        scope: ModificationScope,
    ) -> CandidateDayPlan:
        intent = modification.intent
        restaurant_ids = catalog.restaurant_ids()
        attraction_ids = catalog.attraction_ids()

        if intent in {
            ModificationIntent.CHANGE_RESTAURANT,
            ModificationIntent.REDUCE_COST,
        }:
            return self._cheaper_restaurant_day(
                day_number=day_number,
                existing_day=existing_day,
                restaurant_ids=restaurant_ids,
            )

        if intent == ModificationIntent.CHANGE_ACTIVITY:
            return self._replace_activity_day(
                day_number=day_number,
                existing_day=existing_day,
                attraction_ids=attraction_ids,
                catalog=catalog,
            )

        if intent in {ModificationIntent.CHANGE_PACE, ModificationIntent.MODIFY_DAY}:
            return self._relaxed_day(
                day_number=day_number,
                existing_day=existing_day,
                attraction_ids=attraction_ids,
                catalog=catalog,
            )

        return existing_day

    def _cheaper_restaurant_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        restaurant_ids: list[str],
    ) -> CandidateDayPlan:
        if not restaurant_ids:
            return existing_day
        current_index = 0
        if existing_day.restaurant_source_id in restaurant_ids:
            current_index = restaurant_ids.index(existing_day.restaurant_source_id)
        cheaper_index = (current_index + 1) % len(restaurant_ids)
        return CandidateDayPlan(
            day_number=day_number,
            attraction_source_ids=list(existing_day.attraction_source_ids),
            restaurant_source_id=restaurant_ids[cheaper_index],
        )

    def _replace_activity_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        attraction_ids: list[str],
        catalog: GroundedCatalog,
    ) -> CandidateDayPlan:
        if not attraction_ids:
            return existing_day
        current = (
            existing_day.attraction_source_ids[0]
            if existing_day.attraction_source_ids
            else None
        )
        alternatives = [item for item in attraction_ids if item != current]
        selected = alternatives[0] if alternatives else attraction_ids[0]
        return CandidateDayPlan(
            day_number=day_number,
            attraction_source_ids=[selected],
            restaurant_source_id=existing_day.restaurant_source_id,
        )

    def _relaxed_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        attraction_ids: list[str],
        catalog: GroundedCatalog,
    ) -> CandidateDayPlan:
        if not existing_day.attraction_source_ids:
            selected = select_weather_aware_attractions(
                attraction_ids,
                day_number=day_number,
                catalog=catalog,
                assumptions=self._assumptions,
                max_items=1,
            )
            return CandidateDayPlan(
                day_number=day_number,
                attraction_source_ids=selected,
                restaurant_source_id=existing_day.restaurant_source_id,
            )
        return CandidateDayPlan(
            day_number=day_number,
            attraction_source_ids=[existing_day.attraction_source_ids[0]],
            restaurant_source_id=existing_day.restaurant_source_id,
        )


def existing_candidate_from_context(
    context: ItineraryBuildContext,
    *,
    previous_itinerary: object,
) -> ItinerarySelectionCandidate:
    from app.itinerary.schemas import Itinerary

    if not isinstance(previous_itinerary, Itinerary):
        msg = "previous itinerary is required for modification composition"
        raise TypeError(msg)
    return candidate_from_itinerary(previous_itinerary)
