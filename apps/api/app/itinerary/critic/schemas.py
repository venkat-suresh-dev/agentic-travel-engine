"""Structured critic result schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CriticIssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class CriticIssueCode(StrEnum):
    DAY_COUNT_MISMATCH = "DAY_COUNT_MISMATCH"
    TIME_OVERLAP = "TIME_OVERLAP"
    TRAVEL_BUFFER_VIOLATION = "TRAVEL_BUFFER_VIOLATION"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"
    UNKNOWN_LOCATION = "UNKNOWN_LOCATION"
    INVALID_COST = "INVALID_COST"
    DAILY_SUBTOTAL_MISMATCH = "DAILY_SUBTOTAL_MISMATCH"
    BUDGET_MISMATCH = "BUDGET_MISMATCH"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MISSING_MEAL = "MISSING_MEAL"
    MISSING_DAY = "MISSING_DAY"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    UNSUPPORTED_ITEM = "UNSUPPORTED_ITEM"
    WEATHER_RULE_VIOLATION = "WEATHER_RULE_VIOLATION"
    REPEATED_ATTRACTION = "REPEATED_ATTRACTION"
    REPEATED_RESTAURANT = "REPEATED_RESTAURANT"
    LOW_CATEGORY_DIVERSITY = "LOW_CATEGORY_DIVERSITY"
    LOW_GEOGRAPHIC_DIVERSITY = "LOW_GEOGRAPHIC_DIVERSITY"
    LOW_LANDMARK_COVERAGE = "LOW_LANDMARK_COVERAGE"
    LOW_PLACE_QUALITY = "LOW_PLACE_QUALITY"
    SPARSE_DAY = "SPARSE_DAY"
    EXCESSIVE_TRAVEL = "EXCESSIVE_TRAVEL"


class CriticIssue(BaseModel):
    """Single deterministic critic finding."""

    model_config = ConfigDict(extra="forbid")

    code: CriticIssueCode
    severity: CriticIssueSeverity
    message: str = Field(min_length=1)
    day_number: int | None = Field(default=None, ge=1)
    item_id: str | None = None
    source_id: str | None = None


class CriticResult(BaseModel):
    """Deterministic critic output for itinerary approval."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    issues: list[CriticIssue] = Field(default_factory=list)
    warnings: list[CriticIssue] = Field(default_factory=list)
    retryable: bool = False
