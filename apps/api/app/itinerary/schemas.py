"""Canonical itinerary domain schemas."""

from __future__ import annotations

from datetime import date as CalendarDate
from datetime import time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.budget.schemas import PriceDataKind


class ItineraryItemCategory(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    TRANSPORT = "transport"
    FREE_TIME = "free_time"
    OTHER = "other"


class ItemCost(BaseModel):
    """Item-level cost with provenance semantics.

    ``amount`` / ``currency`` are the display values (trip currency when a
    conversion was applied). Provider-native amounts stay in
    ``source_amount`` / ``source_currency`` when they differ.
    """

    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)
    is_estimate: bool = False
    data_kind: PriceDataKind
    source_amount: Decimal | None = None
    source_currency: str | None = Field(default=None, min_length=3, max_length=3)


class ItineraryItem(BaseModel):
    """Single schedulable itinerary element."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    day_number: int | None = Field(default=None, ge=1)
    date: CalendarDate | None = None
    start_time: time
    end_time: time
    category: ItineraryItemCategory
    title: str = Field(min_length=1)
    description: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cost: ItemCost
    source: str
    source_id: str | None = None
    data_status: PriceDataKind

    @model_validator(mode="after")
    def validate_time_order(self) -> ItineraryItem:
        if self.end_time <= self.start_time:
            # Overnight flights may arrive on the next calendar day.
            if self.category == ItineraryItemCategory.FLIGHT:
                return self
            msg = "end_time must be after start_time"
            raise ValueError(msg)
        return self


class TravelLeg(BaseModel):
    """Explicit travel interval between two items."""

    model_config = ConfigDict(extra="forbid")

    leg_id: str
    from_item_id: str
    to_item_id: str
    day_number: int = Field(ge=1)
    start_time: time
    end_time: time
    distance_meters: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)
    travel_mode: str
    source: str
    data_status: PriceDataKind

    @model_validator(mode="after")
    def validate_time_order(self) -> TravelLeg:
        if self.end_time <= self.start_time:
            msg = "end_time must be after start_time"
            raise ValueError(msg)
        return self


class MealSuggestion(BaseModel):
    """Required meal suggestion for a day."""

    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1)
    item: ItineraryItem


class ItineraryDay(BaseModel):
    """One day of activities with deterministic subtotal."""

    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1)
    date: CalendarDate | None = None
    day_theme: str | None = None
    theme_subtitle: str | None = None
    items: list[ItineraryItem] = Field(default_factory=list)
    travel_legs: list[TravelLeg] = Field(default_factory=list)
    meal: MealSuggestion | None = None
    subtotal: Decimal
    currency: str = Field(min_length=3, max_length=3)


class Itinerary(BaseModel):
    """Validated day-by-day itinerary."""

    model_config = ConfigDict(extra="forbid")

    days: list[ItineraryDay]
    infrastructure_items: list[ItineraryItem] = Field(default_factory=list)
    currency: str = Field(min_length=3, max_length=3)
    total_estimated_cost: Decimal
    budget_currency: str
    budget_amount: Decimal
    budget_total_cost: Decimal
    budget_remaining: Decimal


class CandidateDayPlan(BaseModel):
    """LLM-produced day plan referencing grounded source IDs only."""

    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1)
    attraction_source_ids: list[str] = Field(default_factory=list)
    restaurant_source_id: str = Field(min_length=1)


class ItinerarySelectionCandidate(BaseModel):
    """Structured LLM composition output."""

    model_config = ConfigDict(extra="forbid")

    days: list[CandidateDayPlan] = Field(min_length=1)


class ItineraryValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    day_number: int | None = None
    item_id: str | None = None


class ItineraryValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    issues: list[ItineraryValidationIssue] = Field(default_factory=list)


class ItineraryBuildResult(BaseModel):
    """Result of itinerary generation and deterministic validation."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    itinerary: Itinerary | None = None
    candidate: ItinerarySelectionCandidate | None = None
    validation: ItineraryValidationResult
    composer_provider: str | None = None
