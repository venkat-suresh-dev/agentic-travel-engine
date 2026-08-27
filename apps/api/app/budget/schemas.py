"""Typed contracts for the deterministic budget engine."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BudgetCategory(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    FOOD = "food"
    ACTIVITY = "activity"
    TRANSPORT = "transport"
    OTHER = "other"


class PriceDataKind(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    ESTIMATED = "estimated"
    FREE = "free"
    REFERENCE = "reference"
    UNAVAILABLE = "unavailable"


class CategoryInput(BaseModel):
    """Single budget category input with provenance."""

    model_config = ConfigDict(extra="forbid")

    category: BudgetCategory
    source_amount: Decimal | None = None
    source_currency: str | None = None
    budget_amount: Decimal | None = None
    is_estimate: bool = False
    basis: str = Field(min_length=1)
    assumption: str | None = None
    data_kind: PriceDataKind
    source_offer_id: str | None = None
    conversion_note: str | None = None


class BudgetInputs(BaseModel):
    """Explicit inputs for deterministic budget calculation."""

    model_config = ConfigDict(extra="forbid")

    travelers: int = Field(ge=1)
    duration_days: int = Field(ge=0)
    budget_amount: Decimal = Field(ge=0)
    budget_currency: str = Field(min_length=3, max_length=3)
    categories: list[CategoryInput] = Field(default_factory=list)


class CategoryTotal(BaseModel):
    """Computed category total with provenance."""

    model_config = ConfigDict(extra="forbid")

    category: BudgetCategory
    amount: Decimal | None
    currency: str
    source_amount: Decimal | None = None
    source_currency: str | None = None
    is_estimate: bool
    basis: str
    assumption: str | None = None
    data_kind: PriceDataKind
    source_offer_id: str | None = None
    conversion_note: str | None = None
    included_in_total: bool


class BudgetResult(BaseModel):
    """Authoritative deterministic budget computation output."""

    model_config = ConfigDict(extra="forbid")

    currency: str
    budget_amount: Decimal
    flight_cost: Decimal | None = None
    hotel_cost: Decimal | None = None
    food_cost: Decimal | None = None
    activity_cost: Decimal | None = None
    transport_cost: Decimal | None = None
    other_cost: Decimal | None = None
    total_cost: Decimal
    remaining: Decimal
    budget_exceeded: bool
    variance: Decimal
    categories: list[CategoryTotal] = Field(default_factory=list)
    unavailable_categories: list[BudgetCategory] = Field(default_factory=list)
    is_authoritative: bool = True
