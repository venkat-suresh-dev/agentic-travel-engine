"""Provider-independent weather schemas."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WeatherDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class WeatherForecastRequest(BaseModel):
    """Narrow weather tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: str = Field(min_length=1)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_window(self) -> WeatherForecastRequest:
        if self.end_date < self.start_date:
            msg = "end_date must be on or after start_date"
            raise ValueError(msg)
        return self


class DailyForecast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None
    precipitation_probability_max: int | None = Field(default=None, ge=0, le=100)
    weather_summary: str
    weather_code: int | None = None


class WeatherForecastResult(BaseModel):
    """Normalized weather response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    location: str
    latitude: float | None = None
    longitude: float | None = None
    source: str
    retrieved_at: datetime
    data_status: WeatherDataStatus
    forecast: list[DailyForecast] = Field(default_factory=list)
    error_message: str | None = None

    @classmethod
    def unavailable(
        cls,
        *,
        location: str,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> WeatherForecastResult:
        return cls(
            location=location,
            source=source,
            retrieved_at=retrieved_at,
            data_status=WeatherDataStatus.UNAVAILABLE,
            forecast=[],
            error_message=error_message,
        )


class WeatherToolMetadata(BaseModel):
    """Observability metadata for a weather tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: WeatherDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
