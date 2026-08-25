"""Provider-independent restaurant and attraction search schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlacesDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


SEARCH_RESULT_DISCLAIMER = (
    "Search results only; ratings, prices, hours, and availability are not "
    "guaranteed and do not constitute a booking or reservation."
)


class RestaurantCuisine(StrEnum):
    ITALIAN = "italian"
    INDIAN = "indian"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    MEXICAN = "mexican"
    FRENCH = "french"
    AMERICAN = "american"
    MEDITERRANEAN = "mediterranean"
    THAI = "thai"
    MIDDLE_EASTERN = "middle_eastern"


class RestaurantPriceLevel(StrEnum):
    INEXPENSIVE = "inexpensive"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"
    VERY_EXPENSIVE = "very_expensive"


class AttractionCategory(StrEnum):
    TOURIST_ATTRACTION = "tourist_attraction"
    MUSEUM = "museum"
    PARK = "park"
    ART_GALLERY = "art_gallery"
    ZOO = "zoo"
    AMUSEMENT_PARK = "amusement_park"
    HISTORICAL_LANDMARK = "historical_landmark"
    PLACE_OF_WORSHIP = "place_of_worship"


SUPPORTED_RESTAURANT_CUISINES = frozenset(RestaurantCuisine)
SUPPORTED_RESTAURANT_PRICE_LEVELS = frozenset(RestaurantPriceLevel)
SUPPORTED_ATTRACTION_CATEGORIES = frozenset(AttractionCategory)

DEFAULT_RADIUS_METERS = 5_000
MIN_RADIUS_METERS = 100
MAX_RADIUS_METERS = 50_000
DEFAULT_MAX_RESULTS = 10
MAX_ALLOWED_RESULTS = 20


class SearchLocation(BaseModel):
    """Normalized search location with coordinates."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class PriceRange(BaseModel):
    """Normalized price range when provided by the upstream API."""

    model_config = ConfigDict(extra="forbid")

    currency: str | None = None
    min_units: int | None = Field(default=None, ge=0)
    max_units: int | None = Field(default=None, ge=0)


class OpeningHours(BaseModel):
    """Normalized opening hours when provided by the upstream API."""

    model_config = ConfigDict(extra="forbid")

    open_now: bool | None = None
    weekday_descriptions: list[str] = Field(default_factory=list)


class RestaurantSearchRequest(BaseModel):
    """Narrow restaurant search tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: SearchLocation
    radius_meters: int = Field(
        default=DEFAULT_RADIUS_METERS,
        ge=MIN_RADIUS_METERS,
        le=MAX_RADIUS_METERS,
    )
    cuisine: RestaurantCuisine | None = None
    price_levels: list[RestaurantPriceLevel] = Field(default_factory=list)
    max_results: int = Field(default=DEFAULT_MAX_RESULTS, ge=1, le=MAX_ALLOWED_RESULTS)
    language_code: str | None = Field(default=None, min_length=2, max_length=10)
    region_code: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("cuisine")
    @classmethod
    def validate_cuisine(
        cls,
        value: RestaurantCuisine | None,
    ) -> RestaurantCuisine | None:
        if value is not None and value not in SUPPORTED_RESTAURANT_CUISINES:
            msg = f"unsupported cuisine: {value}"
            raise ValueError(msg)
        return value

    @field_validator("price_levels")
    @classmethod
    def validate_price_levels(
        cls,
        value: list[RestaurantPriceLevel],
    ) -> list[RestaurantPriceLevel]:
        for level in value:
            if level not in SUPPORTED_RESTAURANT_PRICE_LEVELS:
                msg = f"unsupported price level: {level}"
                raise ValueError(msg)
        return value

    @field_validator("region_code")
    @classmethod
    def normalize_region_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class AttractionSearchRequest(BaseModel):
    """Narrow attraction search tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location: SearchLocation
    radius_meters: int = Field(
        default=DEFAULT_RADIUS_METERS,
        ge=MIN_RADIUS_METERS,
        le=MAX_RADIUS_METERS,
    )
    categories: list[AttractionCategory] = Field(
        default_factory=lambda: [AttractionCategory.TOURIST_ATTRACTION],
        min_length=1,
    )
    max_results: int = Field(default=DEFAULT_MAX_RESULTS, ge=1, le=MAX_ALLOWED_RESULTS)
    language_code: str | None = Field(default=None, min_length=2, max_length=10)
    region_code: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("categories")
    @classmethod
    def validate_categories(
        cls,
        value: list[AttractionCategory],
    ) -> list[AttractionCategory]:
        if not value:
            msg = "categories must not be empty"
            raise ValueError(msg)
        for category in value:
            if category not in SUPPORTED_ATTRACTION_CATEGORIES:
                msg = f"unsupported attraction category: {category}"
                raise ValueError(msg)
        return value

    @field_validator("region_code")
    @classmethod
    def normalize_region_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_location(self) -> AttractionSearchRequest:
        if not self.location.name:
            msg = "location name is required"
            raise ValueError(msg)
        return self


class RestaurantPlace(BaseModel):
    """Normalized restaurant result from a provider search."""

    model_config = ConfigDict(extra="forbid")

    place_id: str
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    primary_type: str | None = None
    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    user_rating_count: int | None = Field(default=None, ge=0)
    price_level: RestaurantPriceLevel | None = None
    price_range: PriceRange | None = None
    opening_hours: OpeningHours | None = None
    website: str | None = None


class AttractionPlace(BaseModel):
    """Normalized attraction result from a provider search."""

    model_config = ConfigDict(extra="forbid")

    place_id: str
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    primary_type: str | None = None
    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    user_rating_count: int | None = Field(default=None, ge=0)
    price_level: RestaurantPriceLevel | None = None
    opening_hours: OpeningHours | None = None
    website: str | None = None


class RestaurantSearchResult(BaseModel):
    """Normalized restaurant search response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: PlacesDataStatus
    restaurants: list[RestaurantPlace] = Field(default_factory=list)
    error_message: str | None = None
    disclaimer: str = SEARCH_RESULT_DISCLAIMER

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> RestaurantSearchResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=PlacesDataStatus.UNAVAILABLE,
            restaurants=[],
            error_message=error_message,
        )


class AttractionSearchResult(BaseModel):
    """Normalized attraction search response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    source: str
    retrieved_at: datetime
    data_status: PlacesDataStatus
    attractions: list[AttractionPlace] = Field(default_factory=list)
    error_message: str | None = None
    disclaimer: str = SEARCH_RESULT_DISCLAIMER

    @classmethod
    def unavailable(
        cls,
        *,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> AttractionSearchResult:
        return cls(
            source=source,
            retrieved_at=retrieved_at,
            data_status=PlacesDataStatus.UNAVAILABLE,
            attractions=[],
            error_message=error_message,
        )


class PlacesToolMetadata(BaseModel):
    """Observability metadata for a places tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: PlacesDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
