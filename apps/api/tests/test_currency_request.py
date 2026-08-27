"""Request builder tests for currency conversion."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.domain.trip_request import TripRequest
from app.tools.currency_request import build_currency_conversion_plan
from mcp_tools.flights.schemas import (
    CabinClass,
    FlightDataStatus,
    FlightOffer,
    FlightSearchResult,
)
from mcp_tools.hotels.schemas import (
    HotelDataStatus,
    HotelOffer,
    HotelSearchResult,
    MoneyAmount,
)


def _trip() -> TripRequest:
    return TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        departure_city="Mumbai",
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


def _hotel_search_with_currency(
    currency: str, amount: str = "2122"
) -> HotelSearchResult:
    return HotelSearchResult(
        source="stayingapi",
        retrieved_at=datetime(2026, 3, 25, 12, 0, 0),
        data_status=HotelDataStatus.LIVE,
        hotels=[
            HotelOffer(
                hotel_id="hotel-eur-1",
                name="Apartments Abramovic 2",
                location="Dubai",
                check_in=date(2026, 12, 1),
                check_out=date(2026, 12, 6),
                total_price=MoneyAmount(amount=Decimal(amount), currency=currency),
            )
        ],
    )


def test_build_currency_conversion_plan_from_flight_offer() -> None:
    plan = build_currency_conversion_plan(
        _trip(),
        _flight_search_with_currency("USD", "500"),
    )
    assert plan is not None
    assert plan.request.base_currency == "USD"
    assert plan.request.quote_currency == "INR"
    assert plan.request.amount == Decimal("500")
    assert plan.source_offer_id == "offer-1"
    assert plan.source_context == "flight_lowest_offer"


def test_build_currency_conversion_plan_prefers_foreign_hotel_over_inr_flight() -> None:
    plan = build_currency_conversion_plan(
        _trip(),
        _flight_search_with_currency("INR", "92712"),
        _hotel_search_with_currency("EUR", "2122"),
    )
    assert plan is not None
    assert plan.request.base_currency == "EUR"
    assert plan.request.quote_currency == "INR"
    assert plan.request.amount == Decimal("2122")
    assert plan.source_context == "hotel_total"
    assert plan.source_offer_id == "hotel-eur-1"


def test_build_currency_conversion_plan_skips_when_all_match_budget_currency() -> None:
    plan = build_currency_conversion_plan(
        _trip(),
        _flight_search_with_currency("INR"),
        _hotel_search_with_currency("INR", "35000"),
    )
    assert plan is None


def test_build_currency_conversion_plan_skips_without_budget_currency() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        duration_days=5,
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency=None,
        departure_city="Mumbai",
    )
    plan = build_currency_conversion_plan(
        trip_request,
        _flight_search_with_currency("USD"),
    )
    assert plan is None


def test_build_currency_conversion_plan_returns_none_without_offers() -> None:
    empty_search = FlightSearchResult(
        source="amadeus",
        retrieved_at=datetime(2026, 3, 25, 12, 0, 0),
        data_status=FlightDataStatus.LIVE,
        offers=[],
    )
    assert build_currency_conversion_plan(_trip(), empty_search) is None
