"""Currency MCP tool tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from mcp_tools.currency.cache import CurrencyCache
from mcp_tools.currency.exceptions import (
    CurrencyMalformedResponseError,
    CurrencyProviderTimeoutError,
)
from mcp_tools.currency.mcp_server import create_currency_mcp_server
from mcp_tools.currency.providers.normalize import parse_frankfurter_rate
from mcp_tools.currency.schemas import (
    CurrencyConversionRequest,
    CurrencyDataStatus,
    RateKind,
    quantize_money,
)
from mcp_tools.currency.service import (
    DETERMINISTIC_SOURCE,
    FRANKFURTER_SOURCE,
    CurrencyService,
)
from tests.fakes import FakeCurrencyRateProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def usd_to_inr_request() -> CurrencyConversionRequest:
    return CurrencyConversionRequest(
        base_currency="usd",
        quote_currency="inr",
        amount=Decimal("500.00"),
    )


def test_valid_conversion_request_normalizes_currency_codes() -> None:
    request = CurrencyConversionRequest(
        base_currency="usd",
        quote_currency="inr",
        amount=Decimal("100"),
    )
    assert request.base_currency == "USD"
    assert request.quote_currency == "INR"


def test_invalid_currency_code_rejected() -> None:
    with pytest.raises(ValueError):
        CurrencyConversionRequest(
            base_currency="US",
            quote_currency="INR",
            amount=Decimal("100"),
        )


def test_zero_amount_rejected() -> None:
    with pytest.raises(ValueError):
        CurrencyConversionRequest(
            base_currency="USD",
            quote_currency="INR",
            amount=Decimal("0"),
        )


def test_negative_amount_rejected() -> None:
    with pytest.raises(ValueError):
        CurrencyConversionRequest(
            base_currency="USD",
            quote_currency="INR",
            amount=Decimal("-1"),
        )


def test_frankfurter_fixture_normalization() -> None:
    payload = json.loads((FIXTURES_DIR / "frankfurter_rate.json").read_text())
    provider_rate = parse_frankfurter_rate(
        payload,
        base_currency="USD",
        quote_currency="INR",
    )
    assert provider_rate.base_currency == "USD"
    assert provider_rate.quote_currency == "INR"
    assert provider_rate.rate == Decimal("83.12")
    assert provider_rate.rate_date == date(2026, 3, 25)


def test_malformed_provider_response_rejected() -> None:
    with pytest.raises(CurrencyMalformedResponseError):
        parse_frankfurter_rate(
            {"rate": "not-a-number", "date": "2026-03-25"},
            base_currency="USD",
            quote_currency="INR",
        )


def test_live_conversion_has_provenance(
    usd_to_inr_request: CurrencyConversionRequest,
) -> None:
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=CurrencyCache(),
    )
    result, metadata = service.convert_currency(usd_to_inr_request)

    assert result.data_status is CurrencyDataStatus.LIVE
    assert result.source == FRANKFURTER_SOURCE
    assert result.rate_kind is RateKind.REFERENCE
    assert result.rate == Decimal("83.12")
    assert result.converted_amount == Decimal("41560.00")
    assert result.rate_date == date(2026, 3, 25)
    assert result.retrieved_at is not None
    assert metadata.tool_name == "convert_currency"


def test_decimal_multiplication_without_float_artifacts() -> None:
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(
            rates={("USD", "INR"): Decimal("0.3333")}
        ),
        cache=CurrencyCache(),
    )
    request = CurrencyConversionRequest(
        base_currency="USD",
        quote_currency="INR",
        amount=Decimal("100.00"),
    )
    result, _ = service.convert_currency(request)
    assert result.converted_amount == Decimal("33.33")


def test_same_currency_conversion_is_deterministic() -> None:
    provider = FakeCurrencyRateProvider(should_fail=True)
    service = CurrencyService(currency_provider=provider, cache=CurrencyCache())
    request = CurrencyConversionRequest(
        base_currency="INR",
        quote_currency="INR",
        amount=Decimal("150000.00"),
    )

    result, metadata = service.convert_currency(request)

    assert result.source == DETERMINISTIC_SOURCE
    assert result.rate == Decimal("1")
    assert result.converted_amount == Decimal("150000.00")
    assert result.data_status is CurrencyDataStatus.LIVE
    assert metadata.cache_status == "miss"


def test_rounding_policy_half_up() -> None:
    assert quantize_money(Decimal("1.005")) == Decimal("1.01")
    assert quantize_money(Decimal("1.004")) == Decimal("1.00")


def test_provider_timeout_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    class FlakyProvider(FakeCurrencyRateProvider):
        def get_exchange_rate(self, **kwargs):  # type: ignore[no-untyped-def]
            calls["count"] += 1
            if calls["count"] == 1:
                raise CurrencyProviderTimeoutError("timeout")
            return super().get_exchange_rate(**kwargs)

    service = CurrencyService(
        currency_provider=FlakyProvider(),
        cache=CurrencyCache(),
        retry_backoff_seconds=0.0,
    )
    request = CurrencyConversionRequest(
        base_currency="USD",
        quote_currency="INR",
        amount=Decimal("10"),
    )
    result, _ = service.convert_currency(request)
    assert calls["count"] == 2
    assert result.data_status is CurrencyDataStatus.LIVE


def test_cached_fallback_after_provider_failure(
    usd_to_inr_request: CurrencyConversionRequest,
) -> None:
    cache = CurrencyCache()
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=cache,
    )
    service.convert_currency(usd_to_inr_request)

    failing_service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(should_fail=True),
        cache=cache,
    )
    result, metadata = failing_service.convert_currency(usd_to_inr_request)
    assert result.data_status is CurrencyDataStatus.CACHED
    assert metadata.cache_status == "hit"


def test_unavailable_without_cache(
    usd_to_inr_request: CurrencyConversionRequest,
) -> None:
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(should_fail=True),
        cache=CurrencyCache(),
    )
    result, metadata = service.convert_currency(usd_to_inr_request)
    assert result.data_status is CurrencyDataStatus.UNAVAILABLE
    assert result.error_message
    assert metadata.cache_status == "miss"


def test_cache_hit(usd_to_inr_request: CurrencyConversionRequest) -> None:
    cache = CurrencyCache()
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=cache,
    )
    service.convert_currency(usd_to_inr_request)
    service.convert_currency(usd_to_inr_request)
    assert cache.get(CurrencyCache.cache_key(usd_to_inr_request)) is not None


def test_cache_expiry(usd_to_inr_request: CurrencyConversionRequest) -> None:
    cache = CurrencyCache(ttl_seconds=1)
    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=cache,
    )
    service.convert_currency(usd_to_inr_request)
    key = CurrencyCache.cache_key(usd_to_inr_request)
    entry = cache.get(key)
    assert entry is not None
    stale_time = datetime.now(UTC) - timedelta(seconds=2)
    cache._entries[key] = type(entry)(result=entry.result, stored_at=stale_time)
    assert cache.get(key) is None


def test_deterministic_cache_key() -> None:
    request_a = CurrencyConversionRequest(
        base_currency="USD",
        quote_currency="INR",
        amount=Decimal("100"),
    )
    request_b = CurrencyConversionRequest(
        base_currency="USD",
        quote_currency="INR",
        amount=Decimal("100"),
    )
    request_c = CurrencyConversionRequest(
        base_currency="USD",
        quote_currency="EUR",
        amount=Decimal("100"),
    )
    assert CurrencyCache.cache_key(request_a) == CurrencyCache.cache_key(request_b)
    assert CurrencyCache.cache_key(request_a) != CurrencyCache.cache_key(request_c)


@pytest.mark.asyncio
async def test_mcp_tool_contract(usd_to_inr_request: CurrencyConversionRequest) -> None:
    from mcp import Client

    service = CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=CurrencyCache(),
    )
    server = create_currency_mcp_server(service)

    async with Client(server) as client:
        tool_result = await client.call_tool(
            "convert_currency",
            {
                "base_currency": usd_to_inr_request.base_currency,
                "quote_currency": usd_to_inr_request.quote_currency,
                "amount": str(usd_to_inr_request.amount),
            },
        )

    payload = tool_result.structured_content
    assert payload["data_status"] == CurrencyDataStatus.LIVE.value
    assert payload["converted_amount"] == "41560.00"
