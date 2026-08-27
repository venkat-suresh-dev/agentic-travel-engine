"""Build currency conversion requests from validated trip and tool state."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import CurrencyConversionRequest
from mcp_tools.flights.schemas import FlightDataStatus, FlightSearchResult
from mcp_tools.hotels.schemas import HotelDataStatus, HotelSearchResult

from app.domain.trip_request import TripRequest


class CurrencyConversionPlan:
    """Application-level conversion plan preserving source offer context."""

    def __init__(
        self,
        request: CurrencyConversionRequest,
        *,
        source_context: str,
        source_offer_id: str,
    ) -> None:
        self.request = request
        self.source_context = source_context
        self.source_offer_id = source_offer_id


def build_currency_conversion_plan(
    trip_request: TripRequest,
    flight_search: FlightSearchResult | None,
    hotel_search: HotelSearchResult | None = None,
) -> CurrencyConversionPlan | None:
    """Create a conversion plan for provider amounts not already in budget currency.

    Prefers hotel totals when the hotel currency differs from the trip currency
    (common when flights are already in INR but hotels remain in EUR/USD).
    Falls back to the lowest flight offer when that currency differs.

    Original provider amounts are never mutated by this plan.
    """
    if trip_request.budget_currency is None:
        return None

    target_currency = trip_request.budget_currency.upper()

    hotel_plan = _hotel_conversion_plan(hotel_search, target_currency)
    if hotel_plan is not None:
        return hotel_plan

    return _flight_conversion_plan(flight_search, target_currency)


def _hotel_conversion_plan(
    hotel_search: HotelSearchResult | None,
    target_currency: str,
) -> CurrencyConversionPlan | None:
    if hotel_search is None or hotel_search.data_status == HotelDataStatus.UNAVAILABLE:
        return None
    if not hotel_search.hotels:
        return None

    offer = min(
        hotel_search.hotels,
        key=lambda item: item.total_price.amount if item.total_price else Decimal("0"),
    )
    if offer.total_price is None:
        return None

    source_currency = offer.total_price.currency.upper()
    if source_currency == target_currency:
        return None

    return CurrencyConversionPlan(
        CurrencyConversionRequest(
            base_currency=source_currency,
            quote_currency=target_currency,
            amount=Decimal(str(offer.total_price.amount)),
        ),
        source_context="hotel_total",
        source_offer_id=offer.hotel_id,
    )


def _flight_conversion_plan(
    flight_search: FlightSearchResult | None,
    target_currency: str,
) -> CurrencyConversionPlan | None:
    if (
        flight_search is None
        or flight_search.data_status == FlightDataStatus.UNAVAILABLE
    ):
        return None
    if not flight_search.offers:
        return None

    offer = min(flight_search.offers, key=lambda item: item.price_amount)
    source_currency = offer.price_currency.upper()
    if source_currency == target_currency:
        return None

    return CurrencyConversionPlan(
        CurrencyConversionRequest(
            base_currency=source_currency,
            quote_currency=target_currency,
            amount=Decimal(str(offer.price_amount)),
        ),
        source_context="flight_lowest_offer",
        source_offer_id=offer.offer_id,
    )
