"""Typed orchestration metadata for parallel tool execution."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AggregateRunStatus(StrEnum):
    """Aggregate outcome for a completed tool fan-out run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ToolExecutionStatus(StrEnum):
    """Per-tool orchestration execution status."""

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    SKIPPED = "skipped"


class ToolOrchestrationRecord(BaseModel):
    """Per-tool orchestration trace for a single node execution."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str | None = None
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    status: ToolExecutionStatus
    error_message: str | None = None


class ToolOrchestrationSummary(BaseModel):
    """Run-level orchestration summary populated after tool fan-out."""

    model_config = ConfigDict(extra="forbid")

    run_id: str | None = None
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    aggregate_run_status: AggregateRunStatus
    tool_records: list[ToolOrchestrationRecord] = Field(default_factory=list)
