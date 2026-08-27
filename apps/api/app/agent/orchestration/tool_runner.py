"""Bounded tool execution wrapper for parallel graph nodes."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from app.agent.orchestration.aggregate import is_tool_result_unavailable
from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.schemas import ToolExecutionStatus, ToolOrchestrationRecord
from app.agent.state import AgentState

ToolExecuteResult = tuple[dict[str, Any], str | None]


def _resolve_tool_status(result: dict[str, Any]) -> ToolExecutionStatus:
    for key, value in result.items():
        if key.endswith("_tool_metadata"):
            continue
        if isinstance(value, dict) and is_tool_result_unavailable(value):
            return ToolExecutionStatus.UNAVAILABLE
    return ToolExecutionStatus.SUCCESS


def run_bounded_tool_node(
    *,
    tool_name: str,
    limiter: ToolConcurrencyLimiter,
    execute: Callable[[], ToolExecuteResult],
    forced_status: ToolExecutionStatus | None = None,
) -> AgentState:
    """Execute a tool node with bounded concurrency and orchestration tracing."""
    started_at = datetime.now(UTC)
    started_perf = time.perf_counter()
    status = forced_status or ToolExecutionStatus.SUCCESS
    error_message: str | None = None
    provider: str | None = None
    result: dict[str, Any] = {}

    with limiter.acquire():
        try:
            result, provider = execute()
            if forced_status is None:
                status = _resolve_tool_status(result)
        except Exception as exc:  # noqa: BLE001 - isolate unexpected tool failures
            status = ToolExecutionStatus.ERROR
            error_message = str(exc)
            result = {}

    completed_at = datetime.now(UTC)
    duration_ms = (time.perf_counter() - started_perf) * 1000
    record = ToolOrchestrationRecord(
        tool_name=tool_name,
        provider=provider,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
    )
    return cast(
        AgentState,
        {
            **result,
            "tool_orchestration": [record.model_dump(mode="json")],
        },
    )
