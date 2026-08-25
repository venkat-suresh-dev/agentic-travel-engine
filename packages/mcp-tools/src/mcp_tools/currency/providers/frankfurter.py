"""Frankfurter v2 currency rate provider."""

from __future__ import annotations

from datetime import date

import httpx

from mcp_tools.currency.exceptions import (
    CurrencyMalformedResponseError,
    CurrencyProviderError,
    CurrencyProviderTimeoutError,
    CurrencyRateLimitError,
)
from mcp_tools.currency.providers.base import ProviderExchangeRate
from mcp_tools.currency.providers.normalize import parse_frankfurter_rate

DEFAULT_FRANKFURTER_BASE_URL = "https://api.frankfurter.dev"


class FrankfurterProvider:
    """Fetch reference exchange rates via the Frankfurter v2 API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_FRANKFURTER_BASE_URL,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def get_exchange_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date: date | None = None,
    ) -> ProviderExchangeRate:
        base = base_currency.upper()
        quote = quote_currency.upper()
        path = f"/v2/rate/{base}/{quote}"
        params: dict[str, str] = {}
        if rate_date is not None:
            params["date"] = rate_date.isoformat()

        url = f"{self._base_url}{path}"
        try:
            if self._client is not None:
                response = self._client.get(
                    url,
                    params=params or None,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client() as client:
                    response = client.get(
                        url,
                        params=params or None,
                        timeout=self._timeout_seconds,
                    )
        except httpx.TimeoutException as exc:
            raise CurrencyProviderTimeoutError("frankfurter request timed out") from exc
        except httpx.HTTPError as exc:
            raise CurrencyProviderError("frankfurter request failed") from exc

        if response.status_code == 429:
            raise CurrencyRateLimitError("frankfurter rate limit exceeded")
        if response.status_code >= 400:
            raise CurrencyProviderError(
                f"frankfurter request failed with status {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise CurrencyMalformedResponseError(
                "frankfurter response was not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise CurrencyMalformedResponseError(
                "frankfurter response was not an object"
            )
        return parse_frankfurter_rate(
            payload,
            base_currency=base,
            quote_currency=quote,
        )
