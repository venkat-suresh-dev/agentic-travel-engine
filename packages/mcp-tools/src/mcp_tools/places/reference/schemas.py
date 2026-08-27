"""Schemas for free reference landmark discovery."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReferenceLandmarkStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class SignificanceTier(StrEnum):
    POI = "poi"
    LANDMARK = "landmark"
    REFERENCE_LANDMARK = "reference_landmark"


class LandmarkSearchRequest(BaseModel):
    """Geographic landmark search near a destination center."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    destination_name: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    radius_meters: int = Field(default=15_000, ge=500, le=50_000)
    max_results: int = Field(default=25, ge=1, le=50)


class ReferenceLandmark(BaseModel):
    """A landmark discovered from a public reference source."""

    model_config = ConfigDict(extra="forbid")

    place_id: str
    name: str
    latitude: float
    longitude: float
    source: str
    reference_page_id: int
    description: str | None = None
    significance_tier: SignificanceTier = SignificanceTier.REFERENCE_LANDMARK
    distance_meters: int | None = Field(default=None, ge=0)


class LandmarkSearchResult(BaseModel):
    """Normalized landmark search response."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: ReferenceLandmarkStatus
    landmarks: list[ReferenceLandmark] = Field(default_factory=list)
    error_message: str | None = None

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> LandmarkSearchResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=ReferenceLandmarkStatus.UNAVAILABLE,
            landmarks=[],
            error_message=error_message,
        )
