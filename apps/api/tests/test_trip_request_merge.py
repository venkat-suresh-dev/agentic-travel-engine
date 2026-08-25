"""Unit tests for trip requirement merge invariants."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.agent.trip_request_merge import merge_trip_requests
from app.domain.trip_request import TripRequest, TripType


def test_merge_preserves_existing_when_extracted_field_is_none() -> None:
    existing = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        departure_city="Mumbai",
        budget_amount=Decimal("150000"),
        budget_currency="INR",
    )
    extracted = TripRequest(preferences=["relaxed pace"])

    merged = merge_trip_requests(existing, extracted)

    assert merged.destination == "Dubai"
    assert merged.duration_days == 5
    assert merged.travelers == 2
    assert merged.departure_city == "Mumbai"
    assert merged.budget_amount == Decimal("150000")
    assert merged.budget_currency == "INR"
    assert merged.preferences == ["relaxed pace"]


def test_merge_does_not_erase_existing_value_when_clarification_omits_field() -> None:
    existing = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        departure_city="Mumbai",
    )
    extracted = TripRequest(budget_amount=Decimal("150000"), budget_currency="INR")

    merged = merge_trip_requests(existing, extracted)

    assert merged.destination == "Dubai"
    assert merged.duration_days == 5
    assert merged.travelers == 2
    assert merged.departure_city == "Mumbai"
    assert merged.budget_amount == Decimal("150000")


def test_merge_appends_unique_preferences() -> None:
    existing = TripRequest(destination="Dubai", preferences=["good food"])
    extracted = TripRequest(preferences=["relaxed pace", "good food"])

    merged = merge_trip_requests(existing, extracted)

    assert merged.preferences == ["good food", "relaxed pace"]


def test_merge_updates_budget_currency_only_when_budget_amount_present() -> None:
    existing = TripRequest(
        destination="Dubai",
        budget_amount=Decimal("150000"),
        budget_currency="INR",
    )
    extracted = TripRequest(budget_currency="USD")

    merged = merge_trip_requests(existing, extracted)

    assert merged.budget_currency == "INR"

    extracted_with_amount = TripRequest(
        budget_amount=Decimal("2000"),
        budget_currency="USD",
    )
    merged_with_amount = merge_trip_requests(existing, extracted_with_amount)

    assert merged_with_amount.budget_amount == Decimal("2000")
    assert merged_with_amount.budget_currency == "USD"


def test_merge_updates_explicitly_supplied_fields() -> None:
    existing = TripRequest(
        destination="Dubai",
        travelers=2,
        departure_city="Mumbai",
    )
    extracted = TripRequest(departure_city="Delhi")

    merged = merge_trip_requests(existing, extracted)

    assert merged.departure_city == "Delhi"
    assert merged.destination == "Dubai"
    assert merged.travelers == 2


def test_merge_handles_dates_without_dropping_unrelated_fields() -> None:
    existing = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
    )
    extracted = TripRequest(
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 15),
    )

    merged = merge_trip_requests(existing, extracted)

    assert merged.start_date == date(2026, 12, 10)
    assert merged.end_date == date(2026, 12, 15)
    assert merged.destination == "Dubai"
    assert merged.travelers == 2
    assert merged.budget_amount == Decimal("150000")


def test_merge_regression_full_context_plus_relaxed_pace() -> None:
    existing = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        departure_city="Mumbai",
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        trip_type=TripType.LEISURE,
    )
    extracted = TripRequest(preferences=["relaxed pace"])

    merged = merge_trip_requests(existing, extracted)

    assert merged.destination == "Dubai"
    assert merged.duration_days == 5
    assert merged.travelers == 2
    assert merged.departure_city == "Mumbai"
    assert merged.budget_amount == Decimal("150000")
    assert merged.budget_currency == "INR"
    assert "relaxed pace" in merged.preferences
