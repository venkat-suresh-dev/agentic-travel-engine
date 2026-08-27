"""Modification orchestration for selective itinerary updates."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.builder import build_budget_inputs
from app.budget.engine import BudgetEngine
from app.budget.schemas import BudgetResult
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.builder import ItineraryDraftResult
from app.itinerary.catalog import GroundedCatalog, build_grounded_catalog
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.schemas import (
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
)
from app.itinerary.validator import validate_candidate
from app.modification.candidate import candidate_from_itinerary
from app.modification.composer import ModificationComposer
from app.modification.merger import merge_modified_itinerary
from app.modification.schemas import (
    ModificationIntent,
    ModificationScope,
    TripModificationRequest,
)


class ModificationEngine:
    """Apply selective modifications to an approved itinerary."""

    def __init__(
        self,
        *,
        composer: ModificationComposer | None = None,
        assumptions: SchedulingAssumptions | None = None,
    ) -> None:
        self._composer = composer or ModificationComposer(assumptions=assumptions)
        self._assumptions = assumptions or SchedulingAssumptions()

    def apply(
        self,
        *,
        previous_itinerary: Itinerary,
        context: ItineraryBuildContext,
        modification: TripModificationRequest,
        scope: ModificationScope,
    ) -> ItineraryDraftResult:
        catalog = build_grounded_catalog(
            context,
            indoor_types=self._assumptions.indoor_attraction_types,
        )
        existing_candidate = candidate_from_itinerary(previous_itinerary)
        try:
            composed = self._composer.compose(
                context=context,
                catalog=catalog,
                existing_candidate=existing_candidate,
                modification=modification,
                scope=scope,
                current_hotel_id=_hotel_source_id(previous_itinerary),
            )
        except ValueError as exc:
            return ItineraryDraftResult(
                success=False,
                error_message=str(exc),
                composer_provider=type(self._composer).__name__,
            )

        infeasible = _infeasible_change(
            modification=modification,
            scope=scope,
            previous=previous_itinerary,
            existing_candidate=existing_candidate,
            selected_hotel_id=composed.selected_hotel_id,
            candidate=composed.candidate,
        )
        if infeasible is not None:
            return ItineraryDraftResult(
                success=False,
                error_message=infeasible,
                composer_provider=type(self._composer).__name__,
            )

        candidate = composed.candidate
        candidate_validation = validate_candidate(
            candidate, context=context, catalog=catalog
        )
        if not candidate_validation.is_valid and scope.affected_days:
            return ItineraryDraftResult(
                success=True,
                candidate=candidate,
                composer_provider=type(self._composer).__name__,
            )

        modified_days, infrastructure = self._materialize_affected(
            candidate=candidate,
            context=context,
            catalog=catalog,
            scope=scope,
            relaxed_days=_carry_relaxed_days(
                previous_itinerary,
                composed.relaxed_days,
                modification=modification,
                scope=scope,
            ),
            selected_hotel_id=composed.selected_hotel_id,
        )
        merged = merge_modified_itinerary(
            previous=previous_itinerary,
            modified_days=modified_days,
            scope=scope,
            infrastructure_items=infrastructure,
        )
        merged = self._sync_budget_fields(merged, context.budget_result)
        unchanged = _unchanged_required_targets(
            modification=modification,
            scope=scope,
            previous=previous_itinerary,
            merged=merged,
        )
        if unchanged is not None:
            return ItineraryDraftResult(
                success=False,
                error_message=unchanged,
                composer_provider=type(self._composer).__name__,
            )
        return ItineraryDraftResult(
            success=True,
            itinerary=merged,
            candidate=candidate,
            composer_provider=type(self._composer).__name__,
        )

    def recompute_budget(
        self,
        *,
        context: ItineraryBuildContext,
        itinerary: Itinerary,
    ) -> BudgetResult:
        explicit_activity_cost = _sum_activity_costs(itinerary)
        inputs = build_budget_inputs(
            context.trip_request,
            flight_search=context.flight_search,
            hotel_search=context.hotel_search,
            currency_conversion=context.currency_conversion,
            explicit_activity_cost=explicit_activity_cost,
            selected_hotel_id=_hotel_source_id(itinerary),
        )
        return BudgetEngine().calculate(inputs)

    def _materialize_affected(
        self,
        *,
        candidate: ItinerarySelectionCandidate,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
        scope: ModificationScope,
        relaxed_days: frozenset[int],
        selected_hotel_id: str | None,
    ) -> tuple[list[ItineraryDay], list[ItineraryItem]]:
        full = materialize_itinerary(
            candidate,
            context=context,
            catalog=catalog,
            assumptions=self._assumptions,
            relaxed_days=relaxed_days,
            selected_hotel_id=selected_hotel_id,
        )
        modified_days = [
            day for day in full.days if day.day_number in scope.affected_days
        ]
        return modified_days, full.infrastructure_items

    def sync_budget_fields(
        self,
        itinerary: Itinerary,
        budget_result: BudgetResult,
    ) -> Itinerary:
        return itinerary.model_copy(
            update={
                "budget_currency": budget_result.currency,
                "budget_amount": budget_result.budget_amount,
                "budget_total_cost": budget_result.total_cost,
                "budget_remaining": budget_result.remaining,
            }
        )

    def _sync_budget_fields(
        self,
        itinerary: Itinerary,
        budget_result: BudgetResult,
    ) -> Itinerary:
        return self.sync_budget_fields(itinerary, budget_result)


def _sum_activity_costs(itinerary: Itinerary) -> Decimal:
    total = Decimal("0")
    for day in itinerary.days:
        for item in day.items:
            if item.cost.amount is not None:
                total += item.cost.amount
    return quantize_money(total)


def _hotel_source_id(itinerary: Itinerary) -> str | None:
    for item in itinerary.infrastructure_items:
        if item.category == ItineraryItemCategory.HOTEL and item.source_id:
            return item.source_id
    return None


def _infeasible_change(
    *,
    modification: TripModificationRequest,
    scope: ModificationScope,
    previous: Itinerary,
    existing_candidate: ItinerarySelectionCandidate,
    selected_hotel_id: str | None,
    candidate: ItinerarySelectionCandidate,
) -> str | None:
    if modification.intent == ModificationIntent.CHANGE_HOTEL:
        previous_hotel = _hotel_source_id(previous)
        if selected_hotel_id == previous_hotel:
            return (
                "No alternative hotels are available from the current provider. "
                "Your current hotel is unchanged."
            )
    if modification.intent == ModificationIntent.CHANGE_RESTAURANT:
        for day_number in scope.affected_days:
            before = next(
                (
                    day
                    for day in existing_candidate.days
                    if day.day_number == day_number
                ),
                None,
            )
            after = next(
                (day for day in candidate.days if day.day_number == day_number),
                None,
            )
            if (
                before is not None
                and after is not None
                and before.restaurant_source_id == after.restaurant_source_id
            ):
                return (
                    "No alternative restaurants are available for that meal. "
                    "The current restaurant is unchanged."
                )
    return None


def _unchanged_required_targets(
    *,
    modification: TripModificationRequest,
    scope: ModificationScope,
    previous: Itinerary,
    merged: Itinerary,
) -> str | None:
    if modification.intent == ModificationIntent.CHANGE_HOTEL:
        if _hotel_source_id(merged) == _hotel_source_id(previous):
            return (
                "No alternative hotels are available from the current provider. "
                "Your current hotel is unchanged."
            )
    if modification.intent == ModificationIntent.CHANGE_RESTAURANT:
        for day_number in scope.affected_days:
            before = _restaurant_source_for_day(previous, day_number)
            after = _restaurant_source_for_day(merged, day_number)
            if before == after:
                return (
                    "No alternative restaurants are available for that meal. "
                    "The current restaurant is unchanged."
                )
    if modification.intent == ModificationIntent.CHANGE_PREFERENCE:
        before_sources = [
            source for day in previous.days for source in _attraction_sources(day)
        ]
        after_sources = [
            source for day in merged.days for source in _attraction_sources(day)
        ]
        if before_sources == after_sources:
            return (
                "No grounded alternatives matched that preference. "
                "Your current activities are unchanged."
            )
    return None


def _restaurant_source_for_day(itinerary: Itinerary, day_number: int) -> str | None:
    day = next((item for item in itinerary.days if item.day_number == day_number), None)
    if day is None:
        return None
    if day.meal is not None:
        return day.meal.item.source_id
    for item in day.items:
        if item.category == ItineraryItemCategory.RESTAURANT:
            return item.source_id
    return None


def _attraction_sources(day: ItineraryDay) -> list[str]:
    return [
        item.source_id
        for item in day.items
        if item.category == ItineraryItemCategory.ATTRACTION and item.source_id
    ]


def _carry_relaxed_days(
    previous: Itinerary,
    composed_relaxed: tuple[int, ...],
    *,
    modification: TripModificationRequest,
    scope: ModificationScope,
) -> frozenset[int]:
    relaxed = set(composed_relaxed)
    if modification.intent == ModificationIntent.CHANGE_PACE:
        return frozenset(relaxed)
    for day in previous.days:
        if day.day_number not in scope.affected_days:
            continue
        if any(item.category == ItineraryItemCategory.FREE_TIME for item in day.items):
            relaxed.add(day.day_number)
    return frozenset(relaxed)
