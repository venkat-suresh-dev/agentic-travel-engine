"""Build budget inputs from normalized provider facts and explicit assumptions."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import (
    CurrencyConversionResult,
    CurrencyDataStatus,
    quantize_money,
)
from mcp_tools.flights.schemas import FlightDataStatus, FlightSearchResult
from mcp_tools.hotels.schemas import HotelDataStatus, HotelSearchResult

from app.budget.assumptions import BudgetAssumptions
from app.budget.exceptions import BudgetValidationError
from app.budget.schemas import (
    BudgetCategory,
    BudgetInputs,
    CategoryInput,
    PriceDataKind,
)
from app.domain.trip_request import TripRequest


def build_budget_inputs(
    trip_request: TripRequest,
    *,
    flight_search: FlightSearchResult | None = None,
    hotel_search: HotelSearchResult | None = None,
    currency_conversion: CurrencyConversionResult | None = None,
    assumptions: BudgetAssumptions | None = None,
    explicit_activity_cost: Decimal | None = None,
) -> BudgetInputs:
    """Map normalized tool facts and assumptions into explicit budget inputs."""
    if trip_request.travelers is None or trip_request.travelers < 1:
        raise BudgetValidationError("travelers must be at least 1")
    if trip_request.budget_amount is None:
        raise BudgetValidationError("budget_amount is required")
    if trip_request.budget_currency is None:
        raise BudgetValidationError("budget_currency is required")

    budget_currency = trip_request.budget_currency.upper()
    duration_days = trip_request.duration_days or 0
    travelers = trip_request.travelers
    planning_assumptions = assumptions or BudgetAssumptions()

    categories: list[CategoryInput] = [
        _build_flight_category(
            flight_search=flight_search,
            currency_conversion=currency_conversion,
            budget_currency=budget_currency,
        ),
        _build_hotel_category(
            hotel_search=hotel_search,
            currency_conversion=currency_conversion,
            budget_currency=budget_currency,
        ),
        _build_food_category(
            assumptions=planning_assumptions,
            travelers=travelers,
            duration_days=duration_days,
            budget_currency=budget_currency,
        ),
        _build_activity_category(
            assumptions=planning_assumptions,
            travelers=travelers,
            duration_days=duration_days,
            budget_currency=budget_currency,
            explicit_activity_cost=explicit_activity_cost,
        ),
        _build_transport_category(
            assumptions=planning_assumptions,
            budget_currency=budget_currency,
        ),
        _build_other_category(
            assumptions=planning_assumptions,
            budget_currency=budget_currency,
        ),
    ]

    return BudgetInputs(
        travelers=travelers,
        duration_days=duration_days,
        budget_amount=Decimal(str(trip_request.budget_amount)),
        budget_currency=budget_currency,
        categories=categories,
    )


def _build_flight_category(
    *,
    flight_search: FlightSearchResult | None,
    currency_conversion: CurrencyConversionResult | None,
    budget_currency: str,
) -> CategoryInput:
    if (
        flight_search is None
        or flight_search.data_status == FlightDataStatus.UNAVAILABLE
    ):
        return CategoryInput(
            category=BudgetCategory.FLIGHT,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_flight_search",
            assumption="Flight pricing unavailable; excluded from total.",
        )
    if not flight_search.offers:
        return CategoryInput(
            category=BudgetCategory.FLIGHT,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_flight_search",
            assumption="No flight offers returned; excluded from total.",
        )

    offer = min(flight_search.offers, key=lambda item: item.price_amount)
    source_amount = Decimal(str(offer.price_amount))
    source_currency = offer.price_currency.upper()
    data_kind = _flight_data_kind(flight_search.data_status)

    if currency_conversion is not None and _conversion_usable(currency_conversion):
        if (
            currency_conversion.base_currency == source_currency
            and currency_conversion.quote_currency == budget_currency
            and currency_conversion.source_offer_id == offer.offer_id
        ):
            return CategoryInput(
                category=BudgetCategory.FLIGHT,
                source_amount=source_amount,
                source_currency=source_currency,
                budget_amount=quantize_money(currency_conversion.converted_amount),
                is_estimate=False,
                basis="provider_lowest_offer_converted",
                data_kind=data_kind,
                source_offer_id=offer.offer_id,
                conversion_note="phase_3f_currency_conversion",
            )

    if source_currency == budget_currency:
        return CategoryInput(
            category=BudgetCategory.FLIGHT,
            source_amount=source_amount,
            source_currency=source_currency,
            budget_amount=quantize_money(source_amount),
            is_estimate=False,
            basis="provider_lowest_offer",
            data_kind=data_kind,
            source_offer_id=offer.offer_id,
        )

    return CategoryInput(
        category=BudgetCategory.FLIGHT,
        source_amount=source_amount,
        source_currency=source_currency,
        data_kind=PriceDataKind.UNAVAILABLE,
        basis="provider_lowest_offer",
        source_offer_id=offer.offer_id,
        assumption="No normalized budget-currency conversion available for flight.",
    )


def _build_hotel_category(
    *,
    hotel_search: HotelSearchResult | None,
    currency_conversion: CurrencyConversionResult | None,
    budget_currency: str,
) -> CategoryInput:
    if hotel_search is None or hotel_search.data_status == HotelDataStatus.UNAVAILABLE:
        return CategoryInput(
            category=BudgetCategory.HOTEL,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_hotel_search",
            assumption="Hotel pricing unavailable; excluded from total.",
        )
    if not hotel_search.hotels:
        return CategoryInput(
            category=BudgetCategory.HOTEL,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_hotel_search",
            assumption="No hotel offers returned; excluded from total.",
        )

    offer = min(
        hotel_search.hotels,
        key=lambda item: item.total_price.amount if item.total_price else Decimal("0"),
    )
    if offer.total_price is None:
        return CategoryInput(
            category=BudgetCategory.HOTEL,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_lowest_hotel",
            assumption="Hotel offer missing total price.",
        )

    source_amount = Decimal(str(offer.total_price.amount))
    source_currency = offer.total_price.currency.upper()
    data_kind = _hotel_data_kind(hotel_search.data_status)
    converted, note = _convert_amount(
        source_amount=source_amount,
        source_currency=source_currency,
        budget_currency=budget_currency,
        currency_conversion=currency_conversion,
    )
    if converted is None:
        return CategoryInput(
            category=BudgetCategory.HOTEL,
            source_amount=source_amount,
            source_currency=source_currency,
            data_kind=PriceDataKind.UNAVAILABLE,
            basis="provider_lowest_hotel",
            source_offer_id=offer.hotel_id,
            assumption="No exchange rate available for hotel total.",
        )

    return CategoryInput(
        category=BudgetCategory.HOTEL,
        source_amount=source_amount,
        source_currency=source_currency,
        budget_amount=converted,
        is_estimate=False,
        basis="provider_lowest_hotel",
        data_kind=data_kind,
        source_offer_id=offer.hotel_id,
        conversion_note=note,
    )


def _build_food_category(
    *,
    assumptions: BudgetAssumptions,
    travelers: int,
    duration_days: int,
    budget_currency: str,
) -> CategoryInput:
    total = quantize_money(
        assumptions.food_total(travelers=travelers, duration_days=duration_days)
    )
    return CategoryInput(
        category=BudgetCategory.FOOD,
        budget_amount=total,
        source_amount=total,
        source_currency=budget_currency,
        is_estimate=True,
        basis="daily_per_traveler_estimate",
        assumption=(
            f"{assumptions.food_per_traveler_per_day} {budget_currency} "
            "per traveler per day "
            f"for {duration_days} day(s) and {travelers} traveler(s)."
        ),
        data_kind=PriceDataKind.ESTIMATED,
    )


def _build_activity_category(
    *,
    assumptions: BudgetAssumptions,
    travelers: int,
    duration_days: int,
    budget_currency: str,
    explicit_activity_cost: Decimal | None,
) -> CategoryInput:
    if explicit_activity_cost is not None and explicit_activity_cost == Decimal("0"):
        return CategoryInput(
            category=BudgetCategory.ACTIVITY,
            budget_amount=Decimal("0"),
            source_amount=Decimal("0"),
            source_currency=budget_currency,
            is_estimate=False,
            basis="explicit_free_activity",
            assumption="Explicit free activity cost.",
            data_kind=PriceDataKind.FREE,
        )

    if explicit_activity_cost is not None:
        amount = quantize_money(explicit_activity_cost)
        return CategoryInput(
            category=BudgetCategory.ACTIVITY,
            budget_amount=amount,
            source_amount=amount,
            source_currency=budget_currency,
            is_estimate=False,
            basis="explicit_activity_cost",
            assumption="Explicit activity cost supplied by caller.",
            data_kind=PriceDataKind.ESTIMATED,
        )

    total = quantize_money(
        assumptions.activity_total(travelers=travelers, duration_days=duration_days)
    )
    return CategoryInput(
        category=BudgetCategory.ACTIVITY,
        budget_amount=total,
        source_amount=total,
        source_currency=budget_currency,
        is_estimate=True,
        basis="daily_per_traveler_estimate",
        assumption=(
            f"{assumptions.activity_per_traveler_per_day} {budget_currency} "
            f"per traveler per day for {duration_days} day(s) and "
            f"{travelers} traveler(s)."
        ),
        data_kind=PriceDataKind.ESTIMATED,
    )


def _build_transport_category(
    *,
    assumptions: BudgetAssumptions,
    budget_currency: str,
) -> CategoryInput:
    total = quantize_money(assumptions.transport_per_trip)
    return CategoryInput(
        category=BudgetCategory.TRANSPORT,
        budget_amount=total,
        source_amount=total,
        source_currency=budget_currency,
        is_estimate=True,
        basis="trip_level_estimate",
        assumption=(
            f"{assumptions.transport_per_trip} {budget_currency} "
            "local transport estimate."
        ),
        data_kind=PriceDataKind.ESTIMATED,
    )


def _build_other_category(
    *,
    assumptions: BudgetAssumptions,
    budget_currency: str,
) -> CategoryInput:
    total = quantize_money(assumptions.other_per_trip)
    return CategoryInput(
        category=BudgetCategory.OTHER,
        budget_amount=total,
        source_amount=total,
        source_currency=budget_currency,
        is_estimate=True,
        basis="trip_level_estimate",
        assumption=(
            f"{assumptions.other_per_trip} {budget_currency} miscellaneous estimate."
        ),
        data_kind=PriceDataKind.ESTIMATED,
    )


def _conversion_usable(conversion: CurrencyConversionResult) -> bool:
    return conversion.data_status != CurrencyDataStatus.UNAVAILABLE


def _convert_amount(
    *,
    source_amount: Decimal,
    source_currency: str,
    budget_currency: str,
    currency_conversion: CurrencyConversionResult | None,
) -> tuple[Decimal | None, str | None]:
    if source_currency == budget_currency:
        return quantize_money(source_amount), None

    if currency_conversion is None or not _conversion_usable(currency_conversion):
        return None, None

    if (
        source_currency == currency_conversion.base_currency
        and budget_currency == currency_conversion.quote_currency
    ):
        converted = quantize_money(source_amount * currency_conversion.rate)
        return converted, "phase_3f_reference_rate"

    return None, None


def _flight_data_kind(status: FlightDataStatus) -> PriceDataKind:
    if status == FlightDataStatus.CACHED:
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE


def _hotel_data_kind(status: HotelDataStatus) -> PriceDataKind:
    if status == HotelDataStatus.CACHED:
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE
