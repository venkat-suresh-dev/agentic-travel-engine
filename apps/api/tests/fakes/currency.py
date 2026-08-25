"""Fake currency tool wiring for API tests."""

from __future__ import annotations

import pytest
from app.tools.currency import CurrencyTool
from mcp_tools.currency.cache import CurrencyCache
from mcp_tools.currency.service import CurrencyService

from tests.fakes.currency_providers import FakeCurrencyRateProvider


@pytest.fixture
def fake_currency_service() -> CurrencyService:
    return CurrencyService(
        currency_provider=FakeCurrencyRateProvider(),
        cache=CurrencyCache(),
    )


@pytest.fixture
def fake_currency_tool(fake_currency_service: CurrencyService) -> CurrencyTool:
    return CurrencyTool(fake_currency_service)
