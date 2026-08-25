"""Currency conversion service with retry, cache, and degraded-mode behavior."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from mcp_tools.currency.cache import CurrencyCache
from mcp_tools.currency.exceptions import CurrencyToolError, CurrencyValidationError
from mcp_tools.currency.providers.base import CurrencyRateProvider
from mcp_tools.currency.schemas import (
    CurrencyConversionRequest,
    CurrencyConversionResult,
    CurrencyDataStatus,
    CurrencyToolMetadata,
    RateKind,
    quantize_money,
)

FRANKFURTER_SOURCE = "frankfurter"
DETERMINISTIC_SOURCE = "deterministic"
CURRENCY_TOOL_NAME = "convert_currency"
DEFAULT_RETRY_BACKOFF_SECONDS = 0.2


class CurrencyService:
    """Coordinate provider calls, exact conversion math, caching, and provenance."""

    def __init__(
        self,
        *,
        currency_provider: CurrencyRateProvider,
        cache: CurrencyCache | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._currency_provider = currency_provider
        self._cache = cache or CurrencyCache()
        self._retry_backoff_seconds = retry_backoff_seconds

    def convert_currency(
        self,
        request: CurrencyConversionRequest,
        *,
        source_context: str | None = None,
        source_offer_id: str | None = None,
    ) -> tuple[CurrencyConversionResult, CurrencyToolMetadata]:
        started = time.perf_counter()
        cache_key = CurrencyCache.cache_key(request)
        request_args = request.model_dump(mode="json")
        cache_status = "miss"

        try:
            result = self._fetch_with_resilience(
                request,
                cache_key,
                source_context=source_context,
                source_offer_id=source_offer_id,
            )
        except CurrencyValidationError as exc:
            result = CurrencyConversionResult.unavailable(
                base_currency=request.base_currency,
                quote_currency=request.quote_currency,
                input_amount=request.amount,
                source=FRANKFURTER_SOURCE,
                retrieved_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except CurrencyToolError as exc:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.result.model_copy(
                    update={"data_status": CurrencyDataStatus.CACHED},
                )
                cache_status = "hit"
            else:
                result = CurrencyConversionResult.unavailable(
                    base_currency=request.base_currency,
                    quote_currency=request.quote_currency,
                    input_amount=request.amount,
                    source=FRANKFURTER_SOURCE,
                    retrieved_at=datetime.now(UTC),
                    error_message=str(exc),
                )

        latency_ms = (time.perf_counter() - started) * 1000
        metadata = CurrencyToolMetadata(
            tool_name=CURRENCY_TOOL_NAME,
            provider=result.source,
            request_args=request_args,
            response_status=result.data_status,
            latency_ms=latency_ms,
            retrieved_at=result.retrieved_at,
            cache_status=cache_status,
        )
        return result, metadata

    def _fetch_with_resilience(
        self,
        request: CurrencyConversionRequest,
        cache_key: str,
        *,
        source_context: str | None,
        source_offer_id: str | None,
    ) -> CurrencyConversionResult:
        last_error: CurrencyToolError | None = None
        for attempt in range(2):
            try:
                return self._fetch_live(
                    request,
                    cache_key,
                    source_context=source_context,
                    source_offer_id=source_offer_id,
                )
            except CurrencyToolError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff_seconds)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _fetch_live(
        self,
        request: CurrencyConversionRequest,
        cache_key: str,
        *,
        source_context: str | None,
        source_offer_id: str | None,
    ) -> CurrencyConversionResult:
        retrieved_at = datetime.now(UTC)
        if request.base_currency == request.quote_currency:
            result = CurrencyConversionResult(
                base_currency=request.base_currency,
                quote_currency=request.quote_currency,
                rate=Decimal("1"),
                input_amount=request.amount,
                converted_amount=quantize_money(request.amount),
                rate_date=retrieved_at.date(),
                retrieved_at=retrieved_at,
                source=DETERMINISTIC_SOURCE,
                data_status=CurrencyDataStatus.LIVE,
                rate_kind=RateKind.REFERENCE,
                source_context=source_context,
                source_offer_id=source_offer_id,
            )
            self._cache.set(cache_key, result)
            return result

        provider_rate = self._currency_provider.get_exchange_rate(
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
            rate_date=request.rate_date,
        )
        converted_amount = quantize_money(request.amount * provider_rate.rate)
        result = CurrencyConversionResult(
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
            rate=provider_rate.rate,
            input_amount=request.amount,
            converted_amount=converted_amount,
            rate_date=provider_rate.rate_date,
            retrieved_at=retrieved_at,
            source=FRANKFURTER_SOURCE,
            data_status=CurrencyDataStatus.LIVE,
            rate_kind=RateKind.REFERENCE,
            source_context=source_context,
            source_offer_id=source_offer_id,
        )
        self._cache.set(cache_key, result)
        return result


class SupportsCurrencyService(Protocol):
    def convert_currency(
        self,
        request: CurrencyConversionRequest,
        *,
        source_context: str | None = None,
        source_offer_id: str | None = None,
    ) -> tuple[CurrencyConversionResult, CurrencyToolMetadata]: ...
