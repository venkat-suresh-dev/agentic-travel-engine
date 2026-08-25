"""Typed API models for the agent conversation lifecycle."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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


class BudgetSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str
    budget_amount: Decimal
    total_cost: Decimal
    remaining: Decimal
    budget_exceeded: bool
    variance: Decimal


class CriticSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    issue_count: int = 0
    warning_count: int = 0
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aggregate_status: str | None = None
    unavailable_tools: list[str] = Field(default_factory=list)


class PlanningFailureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    attempts: int | None = None


class ModificationFailureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    issues: list[str] = Field(default_factory=list)
    preserved_itinerary: bool = True
