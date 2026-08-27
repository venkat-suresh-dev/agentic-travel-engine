"""Typed API models for the agent conversation lifecycle."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.budget.schemas import BudgetCategory, PriceDataKind


class ConversationOperationType(StrEnum):
    """Explicit classification of the latest user interaction."""

    INITIAL_PLAN = "initial_plan"
    CLARIFICATION = "clarification"
    MODIFICATION = "modification"


class AgentRunStatusResponse(StrEnum):
    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    FAILED = "failed"


class OperationResultResponse(BaseModel):
    """Structured metadata for the latest planning operation."""

    model_config = ConfigDict(extra="forbid")

    operation_type: ConversationOperationType
    status: AgentRunStatusResponse
    affected_days: list[int] = Field(default_factory=list)
    changed_item_ids: list[str] = Field(default_factory=list)
    refreshed_sources: list[str] = Field(default_factory=list)
    budget_changed: bool = False
    summary: str | None = None
    change_facts: list[str] = Field(default_factory=list)


class BudgetCategoryLineResponse(BaseModel):
    """Authoritative per-category budget line from the deterministic engine."""

    model_config = ConfigDict(extra="forbid")

    category: BudgetCategory
    amount: Decimal | None = None
    currency: str
    data_kind: PriceDataKind
    included_in_total: bool = False
    is_estimate: bool = False
    source_amount: Decimal | None = None
    source_currency: str | None = None
    assumption: str | None = None


class BudgetSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str
    budget_amount: Decimal
    total_cost: Decimal
    remaining: Decimal
    budget_exceeded: bool
    variance: Decimal
    categories: list[BudgetCategoryLineResponse] = Field(default_factory=list)


class CriticSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    issue_count: int = 0
    warning_count: int = 0
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolExecutionRecordResponse(BaseModel):
    """Per-tool execution trace exposed to the planner UI."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: str
    data_mode: str
    provider: str | None = None
    duration_ms: float | None = None


class ToolAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aggregate_status: str | None = None
    unavailable_tools: list[str] = Field(default_factory=list)
    duration_ms: float | None = None
    tools: list[ToolExecutionRecordResponse] = Field(default_factory=list)


class PlanningFailureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    attempts: int | None = None


class ModificationFailureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    issues: list[str] = Field(default_factory=list)
    preserved_itinerary: bool = True
