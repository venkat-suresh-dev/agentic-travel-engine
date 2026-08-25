"""In-process hotel search cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from mcp_tools.hotels.schemas import HotelSearchRequest, HotelSearchResult

# Hotel pricing and availability change faster than flights; 2 minutes balances
# freshness with provider load while respecting volatile rate data.
DEFAULT_HOTEL_CACHE_TTL_SECONDS = 120
DEFAULT_HOTEL_CACHE_MAX_ENTRIES = 128


@dataclass(frozen=True, slots=True)
class CachedHotelEntry:
    result: HotelSearchResult
    stored_at: datetime


class HotelCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_HOTEL_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_HOTEL_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedHotelEntry] = {}
        self._lock = Lock()

    @staticmethod
    def cache_key(request: HotelSearchRequest) -> str:
        return (
            f"{request.location}|{request.city_code}|"
            f"{request.check_in.isoformat()}|{request.check_out.isoformat()}|"
            f"{request.travelers}|{request.rooms}|{request.currency}"
        )

    def get(self, key: str) -> CachedHotelEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: HotelSearchResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedHotelEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
