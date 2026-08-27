"""Comprehensive unit tests for the deterministic budget engine."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app.budget.builder import build_budget_inputs
from app.budget.engine import BudgetEngine
from app.budget.exceptions import BudgetValidationError
from app.budget.schemas import (
    BudgetCategory,
    BudgetInputs,
    CategoryInput,
    PriceDataKind,
)
from app.domain.trip_request import TripRequest
from mcp_tools.currency.schemas import CurrencyConversionResult, CurrencyDataStatus
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


def _example_inputs() -> BudgetInputs:
    return BudgetInputs(
        travelers=2,
        duration_days=5,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        categories=[
            CategoryInput(
                category=BudgetCategory.FLIGHT,
                source_amount=Decimal("80000"),
                source_currency="INR",
                budget_amount=Decimal("80000"),
                basis="provider_lowest_offer",
                data_kind=PriceDataKind.LIVE,
            ),
            CategoryInput(
                category=BudgetCategory.HOTEL,
                source_amount=Decimal("35000"),
                source_currency="INR",
                budget_amount=Decimal("35000"),
                basis="provider_lowest_hotel",
                data_kind=PriceDataKind.LIVE,
            ),
            CategoryInput(
                category=BudgetCategory.FOOD,
                budget_amount=Decimal("12000"),
                source_amount=Decimal("12000"),
                source_currency="INR",
                is_estimate=True,
                basis="daily_per_traveler_estimate",
                assumption="Explicit food estimate.",
                data_kind=PriceDataKind.ESTIMATED,
            ),
            CategoryInput(
                category=BudgetCategory.ACTIVITY,
                budget_amount=Decimal("9000"),
                source_amount=Decimal("9000"),
                source_currency="INR",
                is_estimate=False,
                basis="explicit_activity_cost",
                data_kind=PriceDataKind.ESTIMATED,
            ),
            CategoryInput(
                category=BudgetCategory.TRANSPORT,
                budget_amount=Decimal("5000"),
                source_amount=Decimal("5000"),
                source_currency="INR",
                is_estimate=True,
                basis="trip_level_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            ),
            CategoryInput(
                category=BudgetCategory.OTHER,
                budget_amount=Decimal("3000"),
                source_amount=Decimal("3000"),
                source_currency="INR",
                is_estimate=True,
                basis="trip_level_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            ),
        ],
    )


def test_example_budget_totals_match_requirements() -> None:
    result = BudgetEngine().calculate(_example_inputs())

    assert result.total_cost == Decimal("144000.00")
    assert result.remaining == Decimal("6000.00")
    assert result.budget_exceeded is False
    assert result.variance == Decimal("0.00")
    assert result.flight_cost == Decimal("80000.00")
    assert result.food_cost == Decimal("12000.00")


def test_budget_exceeded_and_variance() -> None:
    inputs = _example_inputs().model_copy(update={"budget_amount": Decimal("140000")})
    result = BudgetEngine().calculate(inputs)

    assert result.total_cost == Decimal("144000.00")
    assert result.remaining == Decimal("-4000.00")
    assert result.budget_exceeded is True
    assert result.variance == Decimal("4000.00")


def test_exact_budget_match() -> None:
    inputs = _example_inputs().model_copy(update={"budget_amount": Decimal("144000")})
    result = BudgetEngine().calculate(inputs)

    assert result.remaining == Decimal("0.00")
    assert result.budget_exceeded is False
    assert result.variance == Decimal("0.00")


def test_free_activity_is_zero_and_included() -> None:
    inputs = BudgetInputs(
        travelers=1,
        duration_days=3,
        budget_amount=Decimal("10000"),
        budget_currency="INR",
        categories=[
            CategoryInput(
                category=BudgetCategory.ACTIVITY,
                budget_amount=Decimal("0"),
                source_amount=Decimal("0"),
                source_currency="INR",
                basis="explicit_free_activity",
                data_kind=PriceDataKind.FREE,
            )
        ],
    )
    result = BudgetEngine().calculate(inputs)

    assert result.activity_cost == Decimal("0.00")
    assert result.total_cost == Decimal("0.00")


def test_unavailable_provider_is_excluded_not_zero() -> None:
    inputs = BudgetInputs(
        travelers=2,
        duration_days=5,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        categories=[
            CategoryInput(
                category=BudgetCategory.FLIGHT,
                data_kind=PriceDataKind.UNAVAILABLE,
                basis="provider_flight_search",
            ),
            CategoryInput(
                category=BudgetCategory.FOOD,
                budget_amount=Decimal("12000"),
                source_amount=Decimal("12000"),
                source_currency="INR",
                is_estimate=True,
                basis="daily_per_traveler_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            ),
        ],
    )
    result = BudgetEngine().calculate(inputs)

    assert result.flight_cost is None
    assert result.total_cost == Decimal("12000.00")
    assert BudgetCategory.FLIGHT in result.unavailable_categories


def test_zero_travelers_rejected() -> None:
    inputs = _example_inputs().model_copy(update={"travelers": 0})
    with pytest.raises(BudgetValidationError):
        BudgetEngine().calculate(inputs)


def test_zero_day_trip_estimates_are_zero() -> None:
    inputs = BudgetInputs(
        travelers=2,
        duration_days=0,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        categories=[
            CategoryInput(
                category=BudgetCategory.FOOD,
                budget_amount=Decimal("0"),
                source_amount=Decimal("0"),
                source_currency="INR",
                is_estimate=True,
                basis="daily_per_traveler_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            ),
            CategoryInput(
                category=BudgetCategory.ACTIVITY,
                budget_amount=Decimal("0"),
                source_amount=Decimal("0"),
                source_currency="INR",
                is_estimate=True,
                basis="daily_per_traveler_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            ),
        ],
    )
    result = BudgetEngine().calculate(inputs)

    assert result.food_cost == Decimal("0.00")
    assert result.activity_cost == Decimal("0.00")


def test_decimal_rounding_half_up() -> None:
    inputs = BudgetInputs(
        travelers=1,
        duration_days=1,
        budget_amount=Decimal("100"),
        budget_currency="INR",
        categories=[
            CategoryInput(
                category=BudgetCategory.OTHER,
                budget_amount=Decimal("1.005"),
                source_amount=Decimal("1.005"),
                source_currency="INR",
                is_estimate=True,
                basis="trip_level_estimate",
                data_kind=PriceDataKind.ESTIMATED,
            )
        ],
    )
    result = BudgetEngine().calculate(inputs)
    assert result.total_cost == Decimal("1.01")


def test_regression_same_input_same_output() -> None:
    engine = BudgetEngine()
    inputs = _example_inputs()
    first = engine.calculate(inputs)
    second = engine.calculate(inputs)
    assert first == second


def test_builder_uses_currency_conversion_for_foreign_flight() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    flight_search = FlightSearchResult(
        source="fake",
        retrieved_at=datetime.now(UTC),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="offer-1",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=datetime.now(UTC),
                arrival_at=datetime.now(UTC),
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("500"),
                price_currency="USD",
                itineraries=[],
            )
        ],
    )
    conversion = CurrencyConversionResult(
        base_currency="USD",
        quote_currency="INR",
        rate=Decimal("83.12"),
        input_amount=Decimal("500.00"),
        converted_amount=Decimal("41560.00"),
        rate_date=date.today(),
        retrieved_at=datetime.now(UTC),
        source="frankfurter",
        data_status=CurrencyDataStatus.LIVE,
        source_context="flight_lowest_offer",
        source_offer_id="offer-1",
    )
    inputs = build_budget_inputs(
        trip_request,
        flight_search=flight_search,
        currency_conversion=conversion,
    )
    result = BudgetEngine().calculate(inputs)

    assert result.flight_cost == Decimal("41560.00")
    flight = next(
        item for item in result.categories if item.category == BudgetCategory.FLIGHT
    )
    assert flight.source_amount == Decimal("500")
    assert flight.source_currency == "USD"


def test_builder_marks_missing_flight_conversion_unavailable() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    flight_search = FlightSearchResult(
        source="fake",
        retrieved_at=datetime.now(UTC),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="offer-1",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=datetime.now(UTC),
                arrival_at=datetime.now(UTC),
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("500"),
                price_currency="USD",
                itineraries=[],
            )
        ],
    )
    inputs = build_budget_inputs(trip_request, flight_search=flight_search)
    result = BudgetEngine().calculate(inputs)

    assert result.flight_cost is None
    assert BudgetCategory.FLIGHT in result.unavailable_categories


def test_builder_hotel_nights_from_provider_total() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    hotel_search = HotelSearchResult(
        source="fake",
        retrieved_at=datetime.now(UTC),
        data_status=HotelDataStatus.CACHED,
        hotels=[
            HotelOffer(
                hotel_id="hotel-1",
                name="Test Hotel",
                location="Dubai",
                check_in=date(2026, 1, 1),
                check_out=date(2026, 1, 6),
                total_price=MoneyAmount(amount=Decimal("35000"), currency="INR"),
            )
        ],
    )
    inputs = build_budget_inputs(trip_request, hotel_search=hotel_search)
    result = BudgetEngine().calculate(inputs)

    assert result.hotel_cost == Decimal("35000.00")
    hotel = next(
        item for item in result.categories if item.category == BudgetCategory.HOTEL
    )
    assert hotel.data_kind == PriceDataKind.CACHED


def test_builder_supports_explicit_activity_cost() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=1,
        budget_amount=Decimal("50000"),
        budget_currency="INR",
        duration_days=3,
        departure_city="Mumbai",
    )
    inputs = build_budget_inputs(
        trip_request,
        explicit_activity_cost=Decimal("9000"),
    )
    result = BudgetEngine().calculate(inputs)

    assert result.activity_cost == Decimal("9000.00")
    activity = next(
        item for item in result.categories if item.category == BudgetCategory.ACTIVITY
    )
    assert activity.basis == "explicit_activity_cost"


def test_single_traveler_food_estimate_scales_correctly() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=1,
        budget_amount=Decimal("50000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    inputs = build_budget_inputs(trip_request)
    result = BudgetEngine().calculate(inputs)

    assert result.food_cost == Decimal("6000.00")


def test_assumption_metadata_propagates() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    inputs = build_budget_inputs(trip_request)
    result = BudgetEngine().calculate(inputs)

    food = next(
        item for item in result.categories if item.category == BudgetCategory.FOOD
    )
    assert food.is_estimate is True
    assert food.assumption is not None
    assert "per traveler per day" in food.assumption


def test_builder_converts_hotel_eur_to_inr_with_reference_rate() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    hotel_search = HotelSearchResult(
        source="stayingapi",
        retrieved_at=datetime.now(UTC),
        data_status=HotelDataStatus.LIVE,
        hotels=[
            HotelOffer(
                hotel_id="hotel-eur-1",
                name="Apartments Abramovic 2",
                location="Dubai",
                check_in=date(2026, 1, 1),
                check_out=date(2026, 1, 6),
                total_price=MoneyAmount(amount=Decimal("2122"), currency="EUR"),
            )
        ],
    )
    conversion = CurrencyConversionResult(
        base_currency="EUR",
        quote_currency="INR",
        rate=Decimal("90.00"),
        input_amount=Decimal("2122.00"),
        converted_amount=Decimal("190980.00"),
        rate_date=date.today(),
        retrieved_at=datetime.now(UTC),
        source="frankfurter",
        data_status=CurrencyDataStatus.LIVE,
        source_context="hotel_total",
        source_offer_id="hotel-eur-1",
    )
    inputs = build_budget_inputs(
        trip_request,
        hotel_search=hotel_search,
        currency_conversion=conversion,
    )
    result = BudgetEngine().calculate(inputs)

    hotel = next(
        item for item in result.categories if item.category == BudgetCategory.HOTEL
    )
    assert hotel.included_in_total is True
    assert hotel.amount == Decimal("190980.00")
    assert hotel.currency == "INR"
    assert hotel.source_amount == Decimal("2122")
    assert hotel.source_currency == "EUR"
    assert result.hotel_cost == Decimal("190980.00")


def test_builder_excludes_hotel_when_conversion_unavailable() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    hotel_search = HotelSearchResult(
        source="stayingapi",
        retrieved_at=datetime.now(UTC),
        data_status=HotelDataStatus.LIVE,
        hotels=[
            HotelOffer(
                hotel_id="hotel-eur-1",
                name="Apartments Abramovic 2",
                location="Dubai",
                check_in=date(2026, 1, 1),
                check_out=date(2026, 1, 6),
                total_price=MoneyAmount(amount=Decimal("2122"), currency="EUR"),
            )
        ],
    )
    inputs = build_budget_inputs(trip_request, hotel_search=hotel_search)
    result = BudgetEngine().calculate(inputs)

    hotel = next(
        item for item in result.categories if item.category == BudgetCategory.HOTEL
    )
    assert hotel.included_in_total is False
    assert hotel.amount is None
    assert hotel.source_amount == Decimal("2122")
    assert hotel.source_currency == "EUR"
    assert BudgetCategory.HOTEL in result.unavailable_categories
    assert hotel.assumption is not None
    assert "conversion is unavailable" in hotel.assumption


def test_builder_flight_fare_is_party_total_without_traveler_multiply() -> None:
    """SerpAPI/Amadeus already price for request.travelers; budget must not multiply."""
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    flight_search = FlightSearchResult(
        source="serpapi",
        retrieved_at=datetime.now(UTC),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="cheap",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=datetime.now(UTC),
                arrival_at=datetime.now(UTC),
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("92712"),
                price_currency="INR",
                itineraries=[],
            ),
            FlightOffer(
                offer_id="expensive-earlier",
                carrier="AI",
                origin="BOM",
                destination="DXB",
                departure_at=datetime(2026, 1, 1, 6, 0, 0, tzinfo=UTC),
                arrival_at=datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC),
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("427250"),
                price_currency="INR",
                itineraries=[],
            ),
        ],
    )
    inputs = build_budget_inputs(trip_request, flight_search=flight_search)
    result = BudgetEngine().calculate(inputs)

    flight = next(
        item for item in result.categories if item.category == BudgetCategory.FLIGHT
    )
    assert flight.amount == Decimal("92712.00")
    assert flight.source_offer_id == "cheap"
    assert result.flight_cost == Decimal("92712.00")


def test_builder_preserves_original_currency_for_mixed_providers() -> None:
    trip_request = TripRequest(
        destination="Dubai",
        travelers=2,
        budget_amount=Decimal("150000"),
        budget_currency="INR",
        duration_days=5,
        departure_city="Mumbai",
    )
    flight_search = FlightSearchResult(
        source="serpapi",
        retrieved_at=datetime.now(UTC),
        data_status=FlightDataStatus.LIVE,
        offers=[
            FlightOffer(
                offer_id="offer-inr",
                carrier="EK",
                origin="BOM",
                destination="DXB",
                departure_at=datetime.now(UTC),
                arrival_at=datetime.now(UTC),
                duration="PT3H",
                stops=0,
                cabin_class=CabinClass.ECONOMY,
                price_amount=Decimal("50000"),
                price_currency="INR",
                itineraries=[],
            )
        ],
    )
    hotel_search = HotelSearchResult(
        source="stayingapi",
        retrieved_at=datetime.now(UTC),
        data_status=HotelDataStatus.LIVE,
        hotels=[
            HotelOffer(
                hotel_id="hotel-eur",
                name="Euro Stay",
                location="Dubai",
                check_in=date(2026, 1, 1),
                check_out=date(2026, 1, 6),
                total_price=MoneyAmount(amount=Decimal("1000"), currency="EUR"),
            )
        ],
    )
    conversion = CurrencyConversionResult(
        base_currency="EUR",
        quote_currency="INR",
        rate=Decimal("90"),
        input_amount=Decimal("1000"),
        converted_amount=Decimal("90000"),
        rate_date=date.today(),
        retrieved_at=datetime.now(UTC),
        source="frankfurter",
        data_status=CurrencyDataStatus.LIVE,
        source_context="hotel_total",
        source_offer_id="hotel-eur",
    )
    inputs = build_budget_inputs(
        trip_request,
        flight_search=flight_search,
        hotel_search=hotel_search,
        currency_conversion=conversion,
    )
    result = BudgetEngine().calculate(inputs)

    flight = next(c for c in result.categories if c.category == BudgetCategory.FLIGHT)
    hotel = next(c for c in result.categories if c.category == BudgetCategory.HOTEL)
    assert flight.source_currency == "INR"
    assert flight.amount == Decimal("50000.00")
    assert hotel.source_currency == "EUR"
    assert hotel.source_amount == Decimal("1000")
    assert hotel.amount == Decimal("90000.00")
    assert hotel.currency == "INR"
