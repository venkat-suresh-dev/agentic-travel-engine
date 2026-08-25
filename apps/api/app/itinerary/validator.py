"""Deterministic itinerary validation."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.schemas import PriceDataKind
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import (
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
    ItineraryValidationIssue,
    ItineraryValidationResult,
    TravelLeg,
)


def validate_candidate(
    candidate: ItinerarySelectionCandidate,
    *,
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
) -> ItineraryValidationResult:
    issues: list[ItineraryValidationIssue] = []
    expected_days = context.trip_request.duration_days
    if expected_days is None:
        issues.append(
            ItineraryValidationIssue(
                code="missing_duration_days",
                message="duration_days is required for itinerary validation",
            )
        )
        return ItineraryValidationResult(is_valid=False, issues=issues)

    if len(candidate.days) != expected_days:
        issues.append(
            ItineraryValidationIssue(
                code="day_count_mismatch",
                message=(f"expected {expected_days} days, got {len(candidate.days)}"),
            )
        )

    day_numbers = sorted(day.day_number for day in candidate.days)
    if day_numbers != list(range(1, expected_days + 1)):
        issues.append(
            ItineraryValidationIssue(
                code="invalid_day_sequence",
                message="day numbers must be exactly 1..duration_days",
            )
        )

    for day in candidate.days:
        if not day.restaurant_source_id:
            issues.append(
                ItineraryValidationIssue(
                    code="missing_meal",
                    message="each day requires a restaurant_source_id",
                    day_number=day.day_number,
                )
            )
            continue
        if day.restaurant_source_id not in catalog.restaurants:
            issues.append(
                ItineraryValidationIssue(
                    code="unknown_restaurant_source",
                    message="restaurant source_id is not in grounded catalog",
                    day_number=day.day_number,
                )
            )
        for attraction_id in day.attraction_source_ids:
            if attraction_id not in catalog.attractions:
                issues.append(
                    ItineraryValidationIssue(
                        code="unknown_attraction_source",
                        message="attraction source_id is not in grounded catalog",
                        day_number=day.day_number,
                    )
                )

    return ItineraryValidationResult(is_valid=not issues, issues=issues)


def validate_itinerary(
    itinerary: Itinerary,
    *,
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
) -> ItineraryValidationResult:
    issues: list[ItineraryValidationIssue] = []
    expected_days = context.trip_request.duration_days
    if expected_days is None:
        return ItineraryValidationResult(
            is_valid=False,
            issues=[
                ItineraryValidationIssue(
                    code="missing_duration_days",
                    message="duration_days is required",
                )
            ],
        )

    if len(itinerary.days) != expected_days:
        issues.append(
            ItineraryValidationIssue(
                code="day_count_mismatch",
                message=f"expected {expected_days} itinerary days",
            )
        )

    for day in itinerary.days:
        if day.meal is None:
            issues.append(
                ItineraryValidationIssue(
                    code="missing_meal",
                    message="each day must include a meal suggestion",
                    day_number=day.day_number,
                )
            )
        computed = _sum_day(day)
        if quantize_money(computed) != day.subtotal:
            issues.append(
                ItineraryValidationIssue(
                    code="subtotal_mismatch",
                    message="daily subtotal must match deterministic item sum",
                    day_number=day.day_number,
                )
            )
        _validate_day_schedule(
            day.day_number,
            day.items,
            day.travel_legs,
            issues,
        )
        for item in day.items:
            _validate_item_source(item, catalog, issues)

    for item in itinerary.infrastructure_items:
        _validate_item_source(item, catalog, issues)

    return ItineraryValidationResult(is_valid=not issues, issues=issues)


def _validate_day_schedule(
    day_number: int,
    items: list[ItineraryItem],
    legs: list[TravelLeg],
    issues: list[ItineraryValidationIssue],
) -> None:
    items_by_id = {item.item_id: item for item in items}
    timeline: list[tuple[str, datetime, datetime, str]] = []
    for item in items:
        if item.end_time <= item.start_time:
            issues.append(
                ItineraryValidationIssue(
                    code="invalid_time_range",
                    message="item end_time must be after start_time",
                    day_number=day_number,
                    item_id=item.item_id,
                )
            )
        timeline.append(
            (
                item.item_id,
                _combine(item.start_time),
                _combine(item.end_time),
                "item",
            )
        )
    for leg in legs:
        if leg.end_time <= leg.start_time:
            issues.append(
                ItineraryValidationIssue(
                    code="invalid_time_range",
                    message="travel leg end_time must be after start_time",
                    day_number=day_number,
                    item_id=leg.leg_id,
                )
            )
        timeline.append(
            (
                leg.leg_id,
                _combine(leg.start_time),
                _combine(leg.end_time),
                "travel",
            )
        )
        from_item = items_by_id.get(leg.from_item_id)
        to_item = items_by_id.get(leg.to_item_id)
        if from_item is not None and _combine(leg.start_time) < _combine(
            from_item.end_time
        ):
            issues.append(
                ItineraryValidationIssue(
                    code="travel_buffer_violation",
                    message="travel leg starts before previous item ends",
                    day_number=day_number,
                    item_id=leg.leg_id,
                )
            )
        if to_item is not None and _combine(to_item.start_time) < _combine(
            leg.end_time
        ):
            issues.append(
                ItineraryValidationIssue(
                    code="travel_buffer_violation",
                    message="next item starts before travel leg ends",
                    day_number=day_number,
                    item_id=to_item.item_id,
                )
            )
    timeline.sort(key=lambda entry: entry[1])

    for index in range(1, len(timeline)):
        previous = timeline[index - 1]
        current = timeline[index]
        if current[1] < previous[2]:
            issues.append(
                ItineraryValidationIssue(
                    code="time_overlap",
                    message=f"{current[0]} overlaps {previous[0]}",
                    day_number=day_number,
                    item_id=current[0],
                )
            )


def _validate_item_source(
    item: ItineraryItem,
    catalog: GroundedCatalog,
    issues: list[ItineraryValidationIssue],
) -> None:
    if item.category == ItineraryItemCategory.ATTRACTION:
        if item.source_id not in catalog.attractions:
            issues.append(
                ItineraryValidationIssue(
                    code="unknown_attraction_source",
                    message="attraction item references unknown source_id",
                    day_number=item.day_number,
                    item_id=item.item_id,
                )
            )
    if item.category == ItineraryItemCategory.RESTAURANT:
        if item.source_id not in catalog.restaurants:
            issues.append(
                ItineraryValidationIssue(
                    code="unknown_restaurant_source",
                    message="restaurant item references unknown source_id",
                    day_number=item.day_number,
                    item_id=item.item_id,
                )
            )
    if item.category == ItineraryItemCategory.FLIGHT:
        if item.source_id not in catalog.flights:
            issues.append(
                ItineraryValidationIssue(
                    code="unknown_flight_source",
                    message="flight item references unknown source_id",
                    item_id=item.item_id,
                )
            )
    if item.cost.data_kind == PriceDataKind.UNAVAILABLE and item.cost.amount not in (
        None,
        0,
    ):
        issues.append(
            ItineraryValidationIssue(
                code="unavailable_cost_not_zero",
                message="unavailable cost must not be represented as a priced amount",
                day_number=item.day_number,
                item_id=item.item_id,
            )
        )


def _sum_day(day: ItineraryDay) -> Decimal:
    total = Decimal("0")
    for item in day.items:
        if (
            item.cost.amount is not None
            and item.cost.data_kind != PriceDataKind.UNAVAILABLE
        ):
            total += item.cost.amount
    return total


def _combine(value: time) -> datetime:
    return datetime.combine(datetime.today().date(), value)
