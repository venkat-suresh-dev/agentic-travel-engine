"""Provider-independent distance matrix schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DistanceDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class TravelMode(StrEnum):
    DRIVING = "driving"
    WALKING = "walking"


SUPPORTED_TRAVEL_MODES = frozenset(TravelMode)


class LocationPoint(BaseModel):
    """Normalized geographic location with coordinates."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class DistanceMatrixRequest(BaseModel):
    """Narrow distance matrix tool request contract."""

    model_config = ConfigDict(extra="forbid")

    origins: list[LocationPoint] = Field(min_length=1)
    destinations: list[LocationPoint] = Field(min_length=1)
    travel_mode: TravelMode = TravelMode.DRIVING

    @field_validator("travel_mode")
    @classmethod
    def validate_travel_mode(cls, value: TravelMode) -> TravelMode:
        if value not in SUPPORTED_TRAVEL_MODES:
            msg = f"unsupported travel mode: {value}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_locations(self) -> DistanceMatrixRequest:
        if not self.origins:
            msg = "origins must not be empty"
            raise ValueError(msg)
        if not self.destinations:
            msg = "destinations must not be empty"
            raise ValueError(msg)
        return self


class DistanceRoute(BaseModel):
    """Normalized origin-destination distance and duration."""

    model_config = ConfigDict(extra="forbid")

    origin: LocationPoint
    destination: LocationPoint
    distance_meters: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)
    travel_mode: TravelMode


class DistanceMatrixResult(BaseModel):
    """Normalized distance matrix response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: DistanceDataStatus
    travel_mode: TravelMode
    routes: list[DistanceRoute] = Field(default_factory=list)
    error_message: str | None = None

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        travel_mode: TravelMode,
        error_message: str,
    ) -> DistanceMatrixResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=DistanceDataStatus.UNAVAILABLE,
            travel_mode=travel_mode,
            routes=[],
            error_message=error_message,
        )


class DistanceToolMetadata(BaseModel):
    """Observability metadata for a distance tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: DistanceDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
