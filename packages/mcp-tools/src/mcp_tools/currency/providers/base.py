"""Currency rate provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderExchangeRate:
    """Provider-normalized exchange rate before application conversion."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: date


class CurrencyRateProvider(Protocol):
    """Fetch reference exchange rates from an upstream provider."""

    def get_exchange_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date | None = None,
    ) -> ProviderExchangeRate: ...
