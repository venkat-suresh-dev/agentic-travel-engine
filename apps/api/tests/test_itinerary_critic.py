"""Deterministic itinerary critic tests."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from app.budget.schemas import PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.builder import ItineraryBuilder
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.critic.engine import ItineraryCritic
from app.itinerary.critic.schemas import CriticIssueCode
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.schemas import (
    CandidateDayPlan,
    ItemCost,
    Itinerary,
    ItinerarySelectionCandidate,
)

from tests.itinerary.fixtures import (
    example_candidate,
    example_itinerary_context,
    fast_assumptions,
)


def _approved_draft() -> tuple[ItinerarySelectionCandidate, Itinerary]:
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    context = example_itinerary_context(duration_days=2)
    draft = builder.build_draft_from_context(context)
    assert draft.candidate is not None
    assert draft.itinerary is not None
    return draft.candidate, draft.itinerary


def test_valid_itinerary_passes_critic() -> None:
    context = example_itinerary_context(duration_days=2)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)

    result = ItineraryCritic(fast_assumptions()).critique(
        candidate=candidate,
        itinerary=itinerary,
        context=context,
        catalog=catalog,
    )

    assert result.valid is True
    assert result.issues == []


def test_day_count_mismatch_rejected() -> None:
    context = example_itinerary_context(duration_days=3)
    candidate = example_candidate(duration_days=1)
    _, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=itinerary,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(
        issue.code == CriticIssueCode.DAY_COUNT_MISMATCH for issue in result.issues
    )


def test_unknown_source_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/invented"],
                restaurant_source_id="places/restaurant-a",
            )
        ]
    )

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=None,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(issue.code == CriticIssueCode.UNKNOWN_SOURCE for issue in result.issues)


def test_daily_subtotal_mismatch_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    broken = itinerary.model_copy(deep=True)
    broken.days[0] = broken.days[0].model_copy(update={"subtotal": Decimal("999.00")})

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(
        issue.code == CriticIssueCode.DAILY_SUBTOTAL_MISMATCH for issue in result.issues
    )


def test_budget_mismatch_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    broken = itinerary.model_copy(
        deep=True,
        update={"budget_total_cost": Decimal("1.00")},
    )

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(issue.code == CriticIssueCode.BUDGET_MISMATCH for issue in result.issues)


def test_budget_exceeded_is_warning_not_invalid() -> None:
    context = example_itinerary_context(duration_days=1)
    exceeded_budget = context.budget_result.model_copy(
        update={
            "budget_amount": Decimal("1"),
            "budget_exceeded": True,
            "variance": Decimal("1000"),
            "remaining": Decimal("-1000"),
        }
    )
    context = context.model_copy(update={"budget_result": exceeded_budget})
    builder = ItineraryBuilder(
        composer=FakeItineraryComposer(assumptions=fast_assumptions()),
        assumptions=fast_assumptions(),
    )
    draft = builder.build_draft_from_context(context)
    assert draft.candidate is not None
    assert draft.itinerary is not None
    catalog = build_grounded_catalog(context)

    result = ItineraryCritic().critique(
        candidate=draft.candidate,
        itinerary=draft.itinerary,
        context=context,
        catalog=catalog,
    )

    assert result.valid is True
    assert any(
        warning.code == CriticIssueCode.BUDGET_EXCEEDED for warning in result.warnings
    )


def test_missing_meal_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    broken_day = itinerary.days[0].model_copy(update={"meal": None})

    broken = itinerary.model_copy(deep=True)
    broken.days[0] = broken_day

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(issue.code == CriticIssueCode.MISSING_MEAL for issue in result.issues)


def test_weather_rule_violation_rejected() -> None:
    context = example_itinerary_context(duration_days=1, rainy_day=1)
    catalog = build_grounded_catalog(context)
    candidate = ItinerarySelectionCandidate(
        days=[
            CandidateDayPlan(
                day_number=1,
                attraction_source_ids=["places/park"],
                restaurant_source_id="places/restaurant-a",
            )
        ]
    )
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )

    result = ItineraryCritic(SchedulingAssumptions()).critique(
        candidate=candidate,
        itinerary=itinerary,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(
        issue.code == CriticIssueCode.WEATHER_RULE_VIOLATION for issue in result.issues
    )


def test_time_overlap_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    first = (
        itinerary.days[0]
        .items[0]
        .model_copy(update={"start_time": time(9, 0), "end_time": time(18, 0)})
    )
    broken_day = itinerary.days[0].model_copy(
        update={"items": [first, *itinerary.days[0].items[1:]]}
    )
    broken = itinerary.model_copy(deep=True, update={"days": [broken_day]})

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(issue.code == CriticIssueCode.TIME_OVERLAP for issue in result.issues)


def test_travel_buffer_violation_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    leg = itinerary.days[0].travel_legs[0].model_copy(
        update={"start_time": time(8, 0), "end_time": time(8, 30)}
    )
    broken_day = itinerary.days[0].model_copy(update={"travel_legs": [leg]})
    broken = itinerary.model_copy(deep=True, update={"days": [broken_day]})

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(
        issue.code == CriticIssueCode.TRAVEL_BUFFER_VIOLATION for issue in result.issues
    )


def test_unknown_location_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    item = (
        itinerary.days[0]
        .items[0]
        .model_copy(update={"latitude": None, "longitude": None})
    )
    broken_day = itinerary.days[0].model_copy(update={"items": [item]})
    broken = itinerary.model_copy(deep=True, update={"days": [broken_day]})

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(
        issue.code == CriticIssueCode.UNKNOWN_LOCATION for issue in result.issues
    )


def test_invalid_cost_rejected() -> None:
    context = example_itinerary_context(duration_days=1)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    item = (
        itinerary.days[0]
        .items[0]
        .model_copy(
            update={
                "cost": ItemCost(
                    amount=Decimal("10"),
                    currency="INR",
                    data_kind=PriceDataKind.UNAVAILABLE,
                )
            }
        )
    )
    broken_day = itinerary.days[0].model_copy(update={"items": [item]})
    broken = itinerary.model_copy(deep=True, update={"days": [broken_day]})

    result = ItineraryCritic().critique(
        candidate=candidate,
        itinerary=broken,
        context=context,
        catalog=catalog,
    )

    assert result.valid is False
    assert any(issue.code == CriticIssueCode.INVALID_COST for issue in result.issues)


def test_critic_is_deterministic() -> None:
    context = example_itinerary_context(duration_days=2)
    candidate, itinerary = _approved_draft()
    catalog = build_grounded_catalog(context)
    critic = ItineraryCritic(fast_assumptions())

    first = critic.critique(
        candidate=candidate,
        itinerary=itinerary,
        context=context,
        catalog=catalog,
    )
    second = critic.critique(
        candidate=candidate,
        itinerary=itinerary,
        context=context,
        catalog=catalog,
    )

    assert first == second
