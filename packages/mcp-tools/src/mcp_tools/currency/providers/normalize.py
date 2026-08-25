"""Normalize Frankfurter v2 rate payloads into domain models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from mcp_tools.currency.exceptions import CurrencyMalformedResponseError
from mcp_tools.currency.providers.base import ProviderExchangeRate


def parse_frankfurter_rate(
    payload: dict[str, Any],
    *,
    base_currency: str,
    quote_currency: str,
) -> ProviderExchangeRate:
    """Parse a Frankfurter /v2/rate response."""
    rate_value = payload.get("rate")
    date_value = payload.get("date")
    if rate_value is None or date_value is None:
        raise CurrencyMalformedResponseError("rate response missing rate or date")
    try:
        rate = Decimal(str(rate_value))
        rate_date = date.fromisoformat(str(date_value))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise CurrencyMalformedResponseError("rate response was not parseable") from exc
    if rate <= 0:
        raise CurrencyMalformedResponseError("rate must be positive")
    return ProviderExchangeRate(
        base_currency=base_currency.upper(),
        quote_currency=quote_currency.upper(),
        rate=rate,
        rate_date=rate_date,
    )
