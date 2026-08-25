"""Convert currencies for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import (
    AgentState,
    GraphStatus,
    flight_search_from_state,
    trip_request_from_state,
)
from app.tools.currency import CurrencyTool
from app.tools.currency_request import build_currency_conversion_plan


def build_convert_currency_node(
    currency_tool: CurrencyTool,
) -> Callable[[AgentState], AgentState]:
    """Create a currency conversion node bound to the provided tool."""

    def convert_currency(state: AgentState) -> AgentState:
        """Convert the lowest flight offer into the trip budget currency."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {"status": GraphStatus.COMPLETE.value}

        plan = build_currency_conversion_plan(
            trip_request,
            flight_search_from_state(state),
        )
        if plan is None:
            return {"status": GraphStatus.COMPLETE.value}

        result, metadata = currency_tool.convert_currency(
            plan.request,
            source_context=plan.source_context,
            source_offer_id=plan.source_offer_id,
        )

        return {
            "currency_conversion": result.model_dump(mode="json"),
            "currency_tool_metadata": metadata.model_dump(mode="json"),
            "status": GraphStatus.COMPLETE.value,
        }

    return convert_currency
