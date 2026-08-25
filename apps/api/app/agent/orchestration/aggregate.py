"""Aggregate status computation for parallel tool orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from mcp_tools.currency.schemas import CurrencyDataStatus
from mcp_tools.distance.schemas import DistanceDataStatus
from mcp_tools.flights.schemas import FlightDataStatus
from mcp_tools.hotels.schemas import HotelDataStatus
from mcp_tools.places.schemas import PlacesDataStatus
from mcp_tools.weather.schemas import WeatherDataStatus

from app.agent.orchestration.schemas import (
    AggregateRunStatus,
    ToolExecutionStatus,
    ToolOrchestrationRecord,
    ToolOrchestrationSummary,
)
from app.agent.state import AgentState

INDEPENDENT_TOOL_NAMES: tuple[str, ...] = (
    "fetch_weather",
    "search_flights",
    "search_hotels",
    "get_distance_matrix",
    "search_restaurants",
    "search_attractions",
)

_TOOL_RESULT_KEYS: dict[str, str] = {
    "fetch_weather": "weather_forecast",
    "search_flights": "flight_search",
    "search_hotels": "hotel_search",
    "get_distance_matrix": "distance_matrix",
    "search_restaurants": "restaurant_search",
    "search_attractions": "attraction_search",
    "convert_currency": "currency_conversion",
}

_DATA_STATUS_FIELDS = {
    WeatherDataStatus,
    FlightDataStatus,
    HotelDataStatus,
    DistanceDataStatus,
    PlacesDataStatus,
    CurrencyDataStatus,
}


def is_tool_result_unavailable(result: dict[str, Any] | None) -> bool:
    """Return True when a normalized tool result is unavailable."""
    if result is None:
        return True
    data_status = result.get("data_status")
    if data_status is None:
        return True
    return str(data_status) in {"unavailable", WeatherDataStatus.UNAVAILABLE.value}


def _tool_execution_status(
    tool_name: str,
    state: AgentState,
) -> ToolExecutionStatus:
    result_key = _TOOL_RESULT_KEYS.get(tool_name)
    if result_key is not None:
        result = state.get(result_key)
        if result is None:
            record = _find_tool_record(state, tool_name)
            if record is not None:
                return record.status
            return ToolExecutionStatus.ERROR
        if is_tool_result_unavailable(cast(dict[str, Any], result)):
            return ToolExecutionStatus.UNAVAILABLE
        return ToolExecutionStatus.SUCCESS

    record = _find_tool_record(state, tool_name)
    if record is not None:
        return record.status
    return ToolExecutionStatus.ERROR


def _find_tool_record(
    state: AgentState,
    tool_name: str,
) -> ToolOrchestrationRecord | None:
    for raw in state.get("tool_orchestration", []):
        record = ToolOrchestrationRecord.model_validate(raw)
        if record.tool_name == tool_name:
            return record
    return None


def compute_aggregate_run_status(
    state: AgentState,
    *,
    include_currency: bool = False,
) -> AggregateRunStatus:
    """Compute aggregate success/partial/failed status from tool outcomes."""
    tool_names = list(INDEPENDENT_TOOL_NAMES)
    if include_currency:
        tool_names.append("convert_currency")

    statuses = [_tool_execution_status(name, state) for name in tool_names]
    successes = sum(status == ToolExecutionStatus.SUCCESS for status in statuses)
    skipped = sum(status == ToolExecutionStatus.SKIPPED for status in statuses)
    failures = len(statuses) - successes - skipped

    if successes == 0 and failures > 0:
        return AggregateRunStatus.FAILED
    if failures > 0 or skipped > 0:
        return AggregateRunStatus.PARTIAL
    return AggregateRunStatus.SUCCESS


def build_orchestration_summary(
    state: AgentState,
    *,
    aggregate_run_status: AggregateRunStatus,
    started_at: datetime | None = None,
) -> ToolOrchestrationSummary:
    """Build a deterministic orchestration summary from merged state."""
    records = [
        ToolOrchestrationRecord.model_validate(raw)
        for raw in state.get("tool_orchestration", [])
    ]
    records.sort(key=lambda item: item.tool_name)
    completed_at = datetime.now(UTC)
    run_started = started_at or (records[0].started_at if records else completed_at)
    duration_ms = (
        max(
            (record.completed_at - record.started_at).total_seconds() * 1000
            for record in records
        )
        if records
        else 0.0
    )
    return ToolOrchestrationSummary(
        started_at=run_started,
        completed_at=completed_at,
        duration_ms=duration_ms,
        aggregate_run_status=aggregate_run_status,
        tool_records=records,
    )
