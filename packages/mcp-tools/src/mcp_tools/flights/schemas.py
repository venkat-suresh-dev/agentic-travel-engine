"""Provider-independent flight search schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlightDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class CabinClass(StrEnum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


SEARCH_RESULT_DISCLAIMER = (
    "Search results only; prices and availability are not guaranteed and "
    "do not constitute a booking."
)


class FlightSearchRequest(BaseModel):
    """Narrow flight search tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_date: date
    return_date: date | None = None
    travelers: int = Field(ge=1)
    cabin_class: CabinClass = CabinClass.ECONOMY
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("origin", "destination", "currency")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_trip(self) -> FlightSearchRequest:
        if self.origin == self.destination:
            msg = "origin and destination must differ"
            raise ValueError(msg)
        if self.return_date is not None and self.return_date < self.departure_date:
            msg = "return_date must be on or after departure_date"
            raise ValueError(msg)
        return self


class FlightSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration: str
    flight_number: str
    carrier: str


class FlightItinerary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[FlightSegment]
    duration: str
    stops: int


class FlightOffer(BaseModel):
    """Normalized flight offer from a provider search (not a booking)."""

    model_config = ConfigDict(extra="forbid")

    offer_id: str
    carrier: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration: str
    stops: int
    cabin_class: CabinClass
    price_amount: Decimal
    price_currency: str
    itineraries: list[FlightItinerary]
    is_search_result_only: bool = True


class FlightSearchResult(BaseModel):
    """Normalized flight search response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: FlightDataStatus
    offers: list[FlightOffer] = Field(default_factory=list)
    error_message: str | None = None
    disclaimer: str = SEARCH_RESULT_DISCLAIMER

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> FlightSearchResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=FlightDataStatus.UNAVAILABLE,
            offers=[],
            error_message=error_message,
        )


class FlightToolMetadata(BaseModel):
    """Observability metadata for a flight tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: FlightDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
