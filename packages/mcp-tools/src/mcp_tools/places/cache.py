"""In-process places search cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Literal

from mcp_tools.places.schemas import (
    AttractionSearchRequest,
    AttractionSearchResult,
    RestaurantSearchRequest,
    RestaurantSearchResult,
)

# Place listings change more slowly than flight/hotel pricing but faster than
# static geographic facts; 10 minutes balances freshness with provider cost.
DEFAULT_PLACES_CACHE_TTL_SECONDS = 600
DEFAULT_PLACES_CACHE_MAX_ENTRIES = 128

PlacesSearchKind = Literal["restaurant", "attraction"]
PlacesSearchResult = RestaurantSearchResult | AttractionSearchResult
PlacesSearchRequest = RestaurantSearchRequest | AttractionSearchRequest


@dataclass(frozen=True, slots=True)
class CachedPlacesEntry:
    result: PlacesSearchResult
    stored_at: datetime


class PlacesCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_PLACES_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_PLACES_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedPlacesEntry] = {}
        self._lock = Lock()

    @staticmethod
    def restaurant_cache_key(request: RestaurantSearchRequest) -> str:
        cuisine = request.cuisine.value if request.cuisine is not None else ""
        price_levels = ",".join(level.value for level in request.price_levels)
        return (
            f"restaurant|{request.location.name}|"
            f"{round(request.location.latitude, 6)}|"
            f"{round(request.location.longitude, 6)}|"
            f"{request.radius_meters}|{cuisine}|{price_levels}|"
            f"{request.max_results}|{request.language_code or ''}|"
            f"{request.region_code or ''}"
        )

    @staticmethod
    def attraction_cache_key(request: AttractionSearchRequest) -> str:
        categories = ",".join(category.value for category in request.categories)
        return (
            f"attraction|{request.location.name}|"
            f"{round(request.location.latitude, 6)}|"
            f"{round(request.location.longitude, 6)}|"
            f"{request.radius_meters}|{categories}|"
            f"{request.max_results}|{request.language_code or ''}|"
            f"{request.region_code or ''}"
        )

    def get(self, key: str) -> CachedPlacesEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: PlacesSearchResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedPlacesEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
