"""Request builder tests for currency conversion."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from app.domain.trip_request import TripRequest
from app.tools.currency_request import build_currency_conversion_plan
from mcp_tools.currency.exceptions import CurrencyValidationError
from mcp_tools.flights.schemas import (
    CabinClass,
    FlightDataStatus,
    FlightOffer,
    FlightSearchResult,
)


def _flight_search_with_currency(
    currency: str, amount: str = "45000"
) -> FlightSearchResult:
    return FlightSearchResult(
        source="amadeus",
        retrieved_at=datetime(2026, 3, 25, 12, 0, 0),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="offer-1",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=datetime(2026, 12, 1, 8, 0, 0),
                arrival_at=datetime(2026, 12, 1, 10, 0, 0),
                duration="PT2H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal(amount),
                price_currency=currency,
                itineraries=[],
            )
        ],
    )


def test_build_currency_conversion_plan_from_flight_offer() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        departure_city="Mumbai",
    )
    plan = build_currency_conversion_plan(
        trip_request,
        _flight_search_with_currency("USD", "500"),
    )
    assert plan is not None
    assert plan.request.base_currency == "USD"
    assert plan.request.quote_currency == "INR"
    assert plan.request.amount == Decimal("500")
    assert plan.source_offer_id == "offer-1"


def test_build_currency_conversion_plan_requires_budget_currency() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency=None,
        departure_city="Mumbai",
    )
    with pytest.raises(CurrencyValidationError):
        build_currency_conversion_plan(
            trip_request,
            _flight_search_with_currency("USD"),
        )


def test_build_currency_conversion_plan_returns_none_without_offers() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        departure_city="Mumbai",
    )
    empty_search = FlightSearchResult(
        source="amadeus",
        retrieved_at=datetime(2026, 3, 25, 12, 0, 0),
        data_status=FlightDataStatus.LIVE,
        offers=[],
    )
    assert build_currency_conversion_plan(trip_request, empty_search) is None
