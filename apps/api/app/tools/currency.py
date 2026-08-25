"""Currency tool application boundary."""

from __future__ import annotations

from mcp_tools.currency.schemas import (
    CurrencyConversionRequest,
    CurrencyConversionResult,
    CurrencyToolMetadata,
)
from mcp_tools.currency.service import CurrencyService


class CurrencyTool:
    """Invoke the MCP-backed currency conversion capability."""

    def __init__(self, currency_service: CurrencyService | None = None) -> None:
        if currency_service is None:
            msg = "currency_service is required"
            raise ValueError(msg)
        self._currency_service = currency_service

    @property
    def currency_service(self) -> CurrencyService:
        return self._currency_service

    def convert_currency(
        self,
        request: CurrencyConversionRequest,
        *,
        source_context: str | None = None,
        source_offer_id: str | None = None,
    ) -> tuple[CurrencyConversionResult, CurrencyToolMetadata]:
        """Convert an amount using a reference exchange rate with provenance."""
        return self._currency_service.convert_currency(
            request,
            source_context=source_context,
            source_offer_id=source_offer_id,
        )
