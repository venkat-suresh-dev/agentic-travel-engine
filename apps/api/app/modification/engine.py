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
from app.itinerary.schemas import Itinerary, ItineraryDay, ItinerarySelectionCandidate
from app.itinerary.validator import validate_candidate
from app.modification.candidate import candidate_from_itinerary
from app.modification.composer import ModificationComposer
from app.modification.merger import merge_modified_itinerary
from app.modification.schemas import ModificationScope, TripModificationRequest


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
            candidate = self._composer.compose(
                context=context,
                catalog=catalog,
                existing_candidate=existing_candidate,
                modification=modification,
                scope=scope,
            )
        except ValueError as exc:
            return ItineraryDraftResult(
                success=False,
                error_message=str(exc),
                composer_provider=type(self._composer).__name__,
            )

        candidate_validation = validate_candidate(
            candidate, context=context, catalog=catalog
        )
        if not candidate_validation.is_valid and scope.affected_days:
            return ItineraryDraftResult(
                success=True,
                candidate=candidate,
                composer_provider=type(self._composer).__name__,
            )

        modified_days = self._materialize_affected_days(
            candidate=candidate,
            previous_itinerary=previous_itinerary,
            context=context,
            catalog=catalog,
            scope=scope,
        )
        merged = merge_modified_itinerary(
            previous=previous_itinerary,
            modified_days=modified_days,
            scope=scope,
        )
        merged = self._sync_budget_fields(merged, context.budget_result)
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
        )
        return BudgetEngine().calculate(inputs)

    def _materialize_affected_days(
        self,
        *,
        candidate: ItinerarySelectionCandidate,
        previous_itinerary: Itinerary,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
        scope: ModificationScope,
    ) -> list[ItineraryDay]:

        full = materialize_itinerary(
            candidate,
            context=context,
            catalog=catalog,
            assumptions=self._assumptions,
        )
        modified_days: list[ItineraryDay] = []
        for day in full.days:
            if day.day_number in scope.affected_days:
                modified_days.append(day)
        return modified_days

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
