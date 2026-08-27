"""Convert currencies for complete trip requirements."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.schemas import ToolExecutionStatus
from app.agent.orchestration.tool_runner import ToolExecuteResult, run_bounded_tool_node
from app.agent.state import (
    AgentState,
    flight_search_from_state,
    hotel_search_from_state,
    trip_request_from_state,
)
from app.tools.currency import CurrencyTool
from app.tools.currency_request import build_currency_conversion_plan


def build_convert_currency_node(
    currency_tool: CurrencyTool,
    limiter: ToolConcurrencyLimiter,
) -> Callable[[AgentState], AgentState]:
    """Create a currency conversion node bound to the provided tool."""

    def convert_currency(state: AgentState) -> AgentState:
        """Convert foreign provider totals into the trip budget currency."""
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {}

        plan = build_currency_conversion_plan(
            trip_request,
            flight_search_from_state(state),
            hotel_search_from_state(state),
        )
        if plan is None:
            return run_bounded_tool_node(
                tool_name="convert_currency",
                limiter=limiter,
                execute=lambda: ({}, None),
                forced_status=ToolExecutionStatus.SKIPPED,
            )

        def execute() -> ToolExecuteResult:
            result, metadata = currency_tool.convert_currency(
                plan.request,
                source_context=plan.source_context,
                source_offer_id=plan.source_offer_id,
            )
            return (
                {
                    "currency_conversion": result.model_dump(mode="json"),
                    "currency_tool_metadata": metadata.model_dump(mode="json"),
                },
                metadata.provider,
            )

        return run_bounded_tool_node(
            tool_name="convert_currency",
            limiter=limiter,
            execute=execute,
        )

    return convert_currency
