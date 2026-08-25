"""Structured trip requirement models for the planning agent."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripType(StrEnum):
    LEISURE = "leisure"
    BUSINESS = "business"
    FAMILY = "family"
    ADVENTURE = "adventure"
    OTHER = "other"


class TripRequest(BaseModel):
    """Structured trip requirements produced by requirement extraction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1)
    travelers: int | None = Field(default=None, ge=1)
    budget_amount: Decimal | None = Field(default=None, ge=0)
    budget_currency: str | None = Field(default="INR", min_length=3, max_length=3)
    departure_city: str | None = None
    trip_type: TripType | None = None
    preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_window(self) -> TripRequest:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            msg = "end_date must be on or after start_date"
            raise ValueError(msg)
        return self


class ValidationResult(BaseModel):
    """Deterministic validation output for structured trip requirements."""

    model_config = ConfigDict(extra="forbid")

    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)


class ClarificationRequest(BaseModel):
    """Structured clarification request for missing trip requirements."""

    model_config = ConfigDict(extra="forbid")

    missing_fields: list[str]
    prompts: dict[str, str]
    message: str


REQUIRED_TRIP_FIELDS: tuple[str, ...] = (
    "destination",
    "travelers",
    "budget_amount",
    "departure_city",
)

REQUIRED_SCHEDULE_FIELDS: tuple[str, ...] = ("duration_days", "start_date")

FIELD_PROMPTS: dict[str, str] = {
    "destination": "Which destination would you like to visit?",
    "travelers": "How many travelers are going on this trip?",
    "budget_amount": "What is your total trip budget?",
    "departure_city": "Which city will you depart from?",
    "duration_days": "How many days should the trip last?",
    "start_date": "When would you like the trip to start?",
}
