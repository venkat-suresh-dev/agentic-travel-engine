"""Structured trip modification schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ModificationIntent(StrEnum):
    """Supported modification intents mapped to deterministic behavior."""

    MODIFY_DAY = "MODIFY_DAY"
    REPLACE_ITEM = "REPLACE_ITEM"
    CHANGE_PACE = "CHANGE_PACE"
    REDUCE_COST = "REDUCE_COST"
    CHANGE_HOTEL = "CHANGE_HOTEL"
    CHANGE_ACTIVITY = "CHANGE_ACTIVITY"
    CHANGE_RESTAURANT = "CHANGE_RESTAURANT"
    CHANGE_PREFERENCE = "CHANGE_PREFERENCE"
    MODIFY_TRIP_REQUIREMENT = "MODIFY_TRIP_REQUIREMENT"


class ModificationStatus(StrEnum):
    """Lifecycle status for a trip modification attempt."""

    NONE = "none"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class TripModificationRequest(BaseModel):
    """Structured modification request extracted from natural language."""

    model_config = ConfigDict(extra="forbid")

    intent: ModificationIntent
    target_days: list[int] = Field(default_factory=list)
    target_item_ids: list[str] = Field(default_factory=list)
    requested_changes: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    raw_message: str = Field(min_length=1)


class ModificationScope(BaseModel):
    """Deterministic scope of what a modification affects."""

    model_config = ConfigDict(extra="forbid")

    affected_days: list[int] = Field(default_factory=list)
    affected_item_ids: list[str] = Field(default_factory=list)
    affected_trip_fields: list[str] = Field(default_factory=list)
    requires_tool_refresh: bool = False
    requires_budget_recompute: bool = False
    requires_critic: bool = True


class RefreshPlan(BaseModel):
    """Deterministic provider refresh requirements for a modification."""

    model_config = ConfigDict(extra="forbid")

    refresh_weather: bool = False
    refresh_flights: bool = False
    refresh_hotels: bool = False
    refresh_places: bool = False
    refresh_distance: bool = False
    refresh_currency: bool = False
    refresh_rag: bool = False

    @property
    def requires_any_refresh(self) -> bool:
        return any(
            (
                self.refresh_weather,
                self.refresh_flights,
                self.refresh_hotels,
                self.refresh_places,
                self.refresh_distance,
                self.refresh_currency,
                self.refresh_rag,
            )
        )


class ModificationFailure(BaseModel):
    """Structured failure when a modification cannot be applied safely."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    issues: list[str] = Field(default_factory=list)
    preserved_itinerary: bool = True
