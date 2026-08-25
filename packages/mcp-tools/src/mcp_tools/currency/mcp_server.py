"""MCP server exposing the currency conversion tool."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from mcp.server import MCPServer

from mcp_tools.currency.schemas import (
    CurrencyConversionRequest,
    CurrencyConversionResult,
)
from mcp_tools.currency.service import CurrencyService

CURRENCY_MCP_SERVER_NAME = "agentic-travel-currency"


def create_currency_mcp_server(
    currency_service: CurrencyService | None = None,
) -> MCPServer:
    """Create an MCP server with a single currency conversion tool."""
    if currency_service is None:
        msg = "currency_service is required to create the currency MCP server"
        raise ValueError(msg)

    server = MCPServer(CURRENCY_MCP_SERVER_NAME)

    @server.tool()
    def convert_currency(
        base_currency: str,
        quote_currency: str,
        amount: Decimal,
        rate_date: date | None = None,
    ) -> CurrencyConversionResult:
        """Return a normalized reference currency conversion result."""
        request = CurrencyConversionRequest(
            base_currency=base_currency,
            quote_currency=quote_currency,
            amount=amount,
            rate_date=rate_date,
        )
        result, _metadata = currency_service.convert_currency(request)
        return result

    return server
