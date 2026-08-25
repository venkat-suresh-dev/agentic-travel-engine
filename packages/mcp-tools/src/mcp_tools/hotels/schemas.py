"""Provider-independent hotel search schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HotelDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


SEARCH_RESULT_DISCLAIMER = (
    "Search results only; prices, ratings, and room availability are not "
    "guaranteed and do not constitute a booking."
)


class MoneyAmount(BaseModel):
    """Exact monetary value preserving provider currency."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class HotelSearchRequest(BaseModel):
    """Narrow hotel search tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: str = Field(min_length=1)
    city_code: str = Field(min_length=3, max_length=3)
    check_in: date
    check_out: date
    travelers: int = Field(ge=1)
    rooms: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("city_code", "currency")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_stay(self) -> HotelSearchRequest:
        if self.check_out <= self.check_in:
            msg = "check_out must be after check_in"
            raise ValueError(msg)
        if self.travelers < self.rooms:
            msg = "travelers must be at least equal to rooms"
            raise ValueError(msg)
        adults_per_room = (self.travelers + self.rooms - 1) // self.rooms
        if adults_per_room > 9:
            msg = "unsupported occupancy: more than 9 travelers per room"
            raise ValueError(msg)
        return self


class HotelRoomOption(BaseModel):
    """Normalized room/rate option from a provider search."""

    model_config = ConfigDict(extra="forbid")

    room_type: str
    description: str | None = None
    nightly_price: MoneyAmount | None = None
    total_price: MoneyAmount
    is_search_result_only: bool = True


class HotelOffer(BaseModel):
    """Normalized hotel result from a provider search (not a booking)."""

    model_config = ConfigDict(extra="forbid")

    hotel_id: str
    name: str
    location: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating: Decimal | None = None
    amenities: list[str] = Field(default_factory=list)
    room_options: list[HotelRoomOption] = Field(default_factory=list)
    nightly_price: MoneyAmount | None = None
    total_price: MoneyAmount | None = None
    check_in: date
    check_out: date
    is_search_result_only: bool = True


class HotelSearchResult(BaseModel):
    """Normalized hotel search response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: HotelDataStatus
    hotels: list[HotelOffer] = Field(default_factory=list)
    error_message: str | None = None
    disclaimer: str = SEARCH_RESULT_DISCLAIMER

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> HotelSearchResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=HotelDataStatus.UNAVAILABLE,
            hotels=[],
            error_message=error_message,
        )


class HotelToolMetadata(BaseModel):
    """Observability metadata for a hotel tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: HotelDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
