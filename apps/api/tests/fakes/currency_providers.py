"""Fake currency providers for API integration tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from mcp_tools.currency.exceptions import (
    CurrencyMalformedResponseError,
    CurrencyProviderError,
)
from mcp_tools.currency.providers.base import ProviderExchangeRate


class FakeCurrencyRateProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        rates: dict[tuple[str, str], Decimal] | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.rates = rates or {
            ("USD", "INR"): Decimal("83.12"),
            ("INR", "USD"): Decimal("0.01203"),
        }

    def get_exchange_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date | None = None,
    ) -> ProviderExchangeRate:
        if self.should_fail:
            raise CurrencyProviderError("simulated provider failure")
        if self.malformed:
            raise CurrencyMalformedResponseError("simulated malformed response")

        base = base_currency.upper()
        quote = quote_currency.upper()
        rate = self.rates.get((base, quote))
        if rate is None:
            raise CurrencyProviderError(f"simulated missing rate for {base}/{quote}")
        return ProviderExchangeRate(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            rate_date=rate_date or date(2026, 3, 25),
        )
