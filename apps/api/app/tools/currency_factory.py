"""Construct production currency tool dependencies from settings."""

from __future__ import annotations

from mcp_tools.currency.cache import CurrencyCache
from mcp_tools.currency.providers.frankfurter import FrankfurterProvider
from mcp_tools.currency.service import CurrencyService

from app.core.config import Settings, settings
from app.tools.currency import CurrencyTool


def build_currency_service(config: Settings | None = None) -> CurrencyService:
    cfg = config or settings
    provider = FrankfurterProvider(
        base_url=cfg.frankfurter_base_url,
        timeout_seconds=cfg.currency_request_timeout_seconds,
    )
    return CurrencyService(
        currency_provider=provider,
        cache=CurrencyCache(ttl_seconds=cfg.currency_cache_ttl_seconds),
    )


def build_currency_tool(config: Settings | None = None) -> CurrencyTool:
    return CurrencyTool(build_currency_service(config))
