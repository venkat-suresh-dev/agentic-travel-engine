"""Deterministic itinerary critic."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.schemas import PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.critic.mapping import (
    default_severity,
    is_retryable,
    map_validator_issue,
)
from app.itinerary.critic.schemas import (
    CriticIssue,
    CriticIssueCode,
    CriticIssueSeverity,
    CriticResult,
)
from app.itinerary.schemas import (
    Itinerary,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
    ItineraryValidationIssue,
)
from app.itinerary.validator import validate_candidate, validate_itinerary


class ItineraryCritic:
    """Authoritative deterministic critic for itinerary drafts."""

    def __init__(self, assumptions: SchedulingAssumptions | None = None) -> None:
        self._assumptions = assumptions or SchedulingAssumptions()

    def critique(
        self,
        *,
        candidate: ItinerarySelectionCandidate | None,
        itinerary: Itinerary | None,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
    ) -> CriticResult:
        issues: list[CriticIssue] = []
        warnings: list[CriticIssue] = []

        if candidate is None:
            issues.append(
                CriticIssue(
                    code=CriticIssueCode.UNSUPPORTED_ITEM,
                    severity=CriticIssueSeverity.ERROR,
                    message="itinerary candidate is missing",
                )
            )
            return self._result(issues, warnings)

        issues.extend(
            self._map_validator_issues(
                validate_candidate(candidate, context=context, catalog=catalog).issues
            )
        )

        if itinerary is None:
            return self._result(issues, warnings)

        issues.extend(
            self._map_validator_issues(
                validate_itinerary(itinerary, context=context, catalog=catalog).issues
            )
        )
        issues.extend(self._check_budget_consistency(itinerary, context))
        issues.extend(self._check_locations(itinerary))
        issues.extend(self._check_weather_rules(itinerary, catalog))

        if context.budget_result.budget_exceeded:
            warnings.append(
                CriticIssue(
                    code=CriticIssueCode.BUDGET_EXCEEDED,
                    severity=CriticIssueSeverity.WARNING,
                    message=(
                        "trip budget is exceeded by "
                        f"{context.budget_result.variance} "
                        f"{context.budget_result.currency}"
                    ),
                )
            )

        return self._result(issues, warnings)

    def _result(
        self,
        issues: list[CriticIssue],
        warnings: list[CriticIssue],
    ) -> CriticResult:
        deduped_issues = _dedupe_issues(issues)
        valid = not deduped_issues
        retryable = valid or any(is_retryable(issue.code) for issue in deduped_issues)
        return CriticResult(
            valid=valid,
            issues=deduped_issues,
            warnings=_dedupe_issues(warnings),
            retryable=retryable,
        )

    def _map_validator_issues(
        self,
        validator_issues: list[ItineraryValidationIssue],
    ) -> list[CriticIssue]:
        mapped: list[CriticIssue] = []
        for issue in validator_issues:
            code = map_validator_issue(issue)
            mapped.append(
                CriticIssue(
                    code=code,
                    severity=default_severity(code),
                    message=issue.message,
                    day_number=issue.day_number,
                    item_id=issue.item_id,
                    source_id=issue.item_id,
                )
            )
        return mapped

    def _check_budget_consistency(
        self,
        itinerary: Itinerary,
        context: ItineraryBuildContext,
    ) -> list[CriticIssue]:
        budget = context.budget_result
        mismatches: list[str] = []
        if itinerary.budget_total_cost != budget.total_cost:
            mismatches.append("budget_total_cost")
        if itinerary.budget_amount != budget.budget_amount:
            mismatches.append("budget_amount")
        if itinerary.budget_remaining != budget.remaining:
            mismatches.append("budget_remaining")
        if itinerary.budget_currency != budget.currency:
            mismatches.append("budget_currency")
        if not mismatches:
            return []
        return [
            CriticIssue(
                code=CriticIssueCode.BUDGET_MISMATCH,
                severity=CriticIssueSeverity.ERROR,
                message=(
                    "itinerary budget fields are inconsistent with BudgetResult: "
                    + ", ".join(mismatches)
                ),
            )
        ]

    def _check_locations(self, itinerary: Itinerary) -> list[CriticIssue]:
        issues: list[CriticIssue] = []
        for day in itinerary.days:
            for item in day.items:
                if item.category not in {
                    ItineraryItemCategory.ATTRACTION,
                    ItineraryItemCategory.RESTAURANT,
                }:
                    continue
                if item.latitude is None or item.longitude is None:
                    issues.append(
                        CriticIssue(
                            code=CriticIssueCode.UNKNOWN_LOCATION,
                            severity=CriticIssueSeverity.ERROR,
                            message="place-backed item is missing coordinates",
                            day_number=item.day_number,
                            item_id=item.item_id,
                            source_id=item.source_id,
                        )
                    )
        return issues

    def _check_weather_rules(
        self,
        itinerary: Itinerary,
        catalog: GroundedCatalog,
    ) -> list[CriticIssue]:
        issues: list[CriticIssue] = []
        for day in itinerary.days:
            forecast = catalog.weather_by_day.get(day.day_number)
            precip = forecast.precipitation_probability_max if forecast else None
            rainy = (
                precip is not None
                and precip >= self._assumptions.rainy_day_precipitation_threshold
            )
            if not rainy:
                continue
            indoor_available = any(
                attraction.is_indoor for attraction in catalog.attractions.values()
            )
            if not indoor_available:
                continue
            for item in day.items:
                if item.category != ItineraryItemCategory.ATTRACTION:
                    continue
                if item.source_id is None:
                    continue
                attraction = catalog.attractions.get(item.source_id)
                if attraction is None:
                    continue
                if not attraction.is_indoor:
                    issues.append(
                        CriticIssue(
                            code=CriticIssueCode.WEATHER_RULE_VIOLATION,
                            severity=CriticIssueSeverity.ERROR,
                            message=(
                                "outdoor attraction scheduled on a rainy day "
                                "when indoor options exist"
                            ),
                            day_number=day.day_number,
                            item_id=item.item_id,
                            source_id=item.source_id,
                        )
                    )
        return issues


def _dedupe_issues(issues: list[CriticIssue]) -> list[CriticIssue]:
    seen: set[tuple[object, ...]] = set()
    deduped: list[CriticIssue] = []
    for issue in issues:
        key = (
            issue.code,
            issue.severity,
            issue.message,
            issue.day_number,
            issue.item_id,
            issue.source_id,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def sum_itinerary_item_costs(itinerary: Itinerary) -> Decimal:
    total = Decimal("0")
    for day in itinerary.days:
        for item in day.items:
            if (
                item.cost.amount is not None
                and item.cost.data_kind != PriceDataKind.UNAVAILABLE
            ):
                total += item.cost.amount
    return quantize_money(total)
