"""Targeted itinerary composition for modifications."""

from __future__ import annotations

from dataclasses import dataclass

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
from app.modification.selection import (
    re_rank_for_preference,
    reduce_attractions,
    select_different_attraction,
    select_different_restaurant,
    select_hotel,
)


@dataclass(frozen=True, slots=True)
class ModificationComposeResult:
    """Deterministic compose output, including non-LLM scheduling hints."""

    candidate: ItinerarySelectionCandidate
    selected_hotel_id: str | None = None
    relaxed_days: tuple[int, ...] = ()


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
        current_hotel_id: str | None = None,
    ) -> ModificationComposeResult:
        if context.trip_request.duration_days is None:
            msg = "duration_days is required for modification composition"
            raise ValueError(msg)

        selected_hotel_id = current_hotel_id
        relaxed_days: list[int] = []
        if modification.intent == ModificationIntent.CHANGE_HOTEL:
            selected_hotel_id = select_hotel(
                catalog,
                current_id=current_hotel_id,
                prefer_cheaper=True,
            )
            return ModificationComposeResult(
                candidate=existing_candidate,
                selected_hotel_id=selected_hotel_id,
            )

        days = list(existing_candidate.days)
        for day_number in scope.affected_days:
            existing_day = next(
                (day for day in days if day.day_number == day_number),
                None,
            )
            if existing_day is None:
                continue
            composed = self._compose_day(
                day_number=day_number,
                existing_day=existing_day,
                catalog=catalog,
                modification=modification,
            )
            days[day_number - 1] = composed.day
            if composed.relaxed:
                relaxed_days.append(day_number)

        if modification.intent == ModificationIntent.REDUCE_COST and (
            "hotel" in scope.affected_trip_fields
        ):
            selected_hotel_id = select_hotel(
                catalog,
                current_id=current_hotel_id,
                prefer_cheaper=True,
                require_change=False,
            )

        return ModificationComposeResult(
            candidate=ItinerarySelectionCandidate(days=days),
            selected_hotel_id=selected_hotel_id,
            relaxed_days=tuple(relaxed_days),
        )

    def _compose_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        catalog: GroundedCatalog,
        modification: TripModificationRequest,
    ) -> _ComposedDay:
        intent = modification.intent
        message = _request_text(modification)

        if intent in {
            ModificationIntent.CHANGE_RESTAURANT,
            ModificationIntent.REDUCE_COST,
        }:
            prefer_cheaper = intent == ModificationIntent.REDUCE_COST or _wants_cheaper(
                message
            )
            restaurant_id = select_different_restaurant(
                catalog,
                current_id=existing_day.restaurant_source_id,
                prefer_cheaper=prefer_cheaper,
                require_change=intent == ModificationIntent.CHANGE_RESTAURANT,
            )
            attractions = list(existing_day.attraction_source_ids)
            if intent == ModificationIntent.REDUCE_COST:
                attractions = reduce_attractions(attractions, max_items=1)
                if attractions == existing_day.attraction_source_ids:
                    cheaper = select_different_attraction(
                        catalog,
                        current_ids=existing_day.attraction_source_ids,
                        prefer_cheaper=True,
                        max_items=1,
                    )
                    if cheaper:
                        attractions = cheaper
            return _ComposedDay(
                day=CandidateDayPlan(
                    day_number=day_number,
                    attraction_source_ids=attractions,
                    restaurant_source_id=(
                        restaurant_id or existing_day.restaurant_source_id
                    ),
                )
            )

        if intent in {
            ModificationIntent.CHANGE_ACTIVITY,
            ModificationIntent.REPLACE_ITEM,
        }:
            selected = select_different_attraction(
                catalog,
                current_ids=existing_day.attraction_source_ids,
                prefer_cheaper=_wants_cheaper(message),
                max_items=max(1, len(existing_day.attraction_source_ids) or 1),
            )
            return _ComposedDay(
                day=CandidateDayPlan(
                    day_number=day_number,
                    attraction_source_ids=selected,
                    restaurant_source_id=existing_day.restaurant_source_id,
                )
            )

        if intent in {ModificationIntent.CHANGE_PACE, ModificationIntent.MODIFY_DAY}:
            return _ComposedDay(
                day=self._relaxed_day(
                    day_number=day_number,
                    existing_day=existing_day,
                    catalog=catalog,
                ),
                relaxed=True,
            )

        if intent == ModificationIntent.CHANGE_PREFERENCE:
            prefer_culture, avoid_shopping = _preference_flags(message)
            selected = re_rank_for_preference(
                catalog,
                existing_day.attraction_source_ids,
                prefer_culture=prefer_culture,
                avoid_shopping=avoid_shopping,
                max_items=max(1, len(existing_day.attraction_source_ids)),
            )
            if not selected:
                selected = select_weather_aware_attractions(
                    catalog.attraction_ids(),
                    day_number=day_number,
                    catalog=catalog,
                    assumptions=self._assumptions,
                    max_items=1,
                )
            return _ComposedDay(
                day=CandidateDayPlan(
                    day_number=day_number,
                    attraction_source_ids=selected,
                    restaurant_source_id=existing_day.restaurant_source_id,
                )
            )

        return _ComposedDay(day=existing_day)

    def _relaxed_day(
        self,
        *,
        day_number: int,
        existing_day: CandidateDayPlan,
        catalog: GroundedCatalog,
    ) -> CandidateDayPlan:
        attraction_ids = catalog.attraction_ids()
        current = list(existing_day.attraction_source_ids)
        if len(current) > 1:
            selected = reduce_attractions(current, max_items=1)
        elif current:
            selected = current[:1]
        else:
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


@dataclass(frozen=True, slots=True)
class _ComposedDay:
    day: CandidateDayPlan
    relaxed: bool = False


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


def _request_text(modification: TripModificationRequest) -> str:
    parts = [modification.raw_message, *modification.requested_changes]
    return " ".join(part for part in parts if part).lower()


def _wants_cheaper(message: str) -> bool:
    return any(
        token in message
        for token in ("cheap", "cheaper", "budget", "less expensive", "lower cost")
    )


def _preference_flags(message: str) -> tuple[bool, bool]:
    prefer_culture = any(
        token in message for token in ("culture", "museum", "heritage", "history")
    )
    avoid_shopping = "less shopping" in message or (
        "shopping" in message and "less" in message
    )
    return prefer_culture, avoid_shopping
