"""Build currency conversion requests from validated trip and tool state."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.exceptions import CurrencyValidationError
from mcp_tools.currency.schemas import CurrencyConversionRequest
from mcp_tools.flights.schemas import FlightSearchResult

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
) -> CurrencyConversionPlan | None:
    """Create a currency conversion plan from validated trip and flight search data.

    Uses the lowest-priced flight offer amount in its provider currency and converts
    it to the trip budget currency. Original flight offer prices remain unchanged.
    """
    if flight_search is None or not flight_search.offers:
        return None
    if trip_request.budget_currency is None:
        raise CurrencyValidationError(
            "budget_currency is required for currency conversion"
        )

    target_currency = trip_request.budget_currency.upper()
    offer = min(flight_search.offers, key=lambda item: item.price_amount)
    base_currency = offer.price_currency.upper()

    request = CurrencyConversionRequest(
        base_currency=base_currency,
        quote_currency=target_currency,
        amount=Decimal(str(offer.price_amount)),
    )
    return CurrencyConversionPlan(
        request,
        source_context="flight_lowest_offer",
        source_offer_id=offer.offer_id,
    )
