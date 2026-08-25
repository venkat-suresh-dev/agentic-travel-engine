"""Schema validation tests for itinerary models."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest
from app.budget.schemas import PriceDataKind
from app.itinerary.schemas import (
    CandidateDayPlan,
    ItemCost,
    ItineraryItem,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
)
from pydantic import ValidationError

from tests.itinerary.fixtures import example_candidate


def test_valid_itinerary_candidate() -> None:
    candidate = example_candidate(duration_days=3)
    assert len(candidate.days) == 3


def test_invalid_category_rejected() -> None:
    with pytest.raises(ValueError):
        ItineraryItemCategory("invalid")


def test_invalid_time_range_rejected() -> None:
    with pytest.raises(ValidationError):
        ItineraryItem(
            item_id="item-1",
            day_number=1,
            start_time=time(12, 0),
            end_time=time(11, 0),
            category=ItineraryItemCategory.ATTRACTION,
            title="Late start",
            cost=ItemCost(
                amount=Decimal("0"),
                currency="INR",
                data_kind=PriceDataKind.FREE,
            ),
            source="google_places",
            data_status=PriceDataKind.FREE,
        )


def test_missing_source_id_allowed_for_non_place_items() -> None:
    item = ItineraryItem(
        item_id="free-time",
        day_number=1,
        start_time=time(15, 0),
        end_time=time(16, 0),
        category=ItineraryItemCategory.FREE_TIME,
        title="Free time",
        cost=ItemCost(amount=None, currency="INR", data_kind=PriceDataKind.FREE),
        source="planner",
        source_id=None,
        data_status=PriceDataKind.FREE,
    )
    assert item.source_id is None


def test_invalid_day_number_rejected() -> None:
    with pytest.raises(ValidationError):
        CandidateDayPlan(
            day_number=0,
            attraction_source_ids=[],
            restaurant_source_id="places/restaurant-a",
        )


def test_candidate_requires_at_least_one_day() -> None:
    with pytest.raises(ValidationError):
        ItinerarySelectionCandidate(days=[])
