"""In-process distance matrix cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from mcp_tools.distance.schemas import DistanceMatrixRequest, DistanceMatrixResult

# Route geometry is relatively stable; 10 minutes balances freshness with load.
DEFAULT_DISTANCE_CACHE_TTL_SECONDS = 600
DEFAULT_DISTANCE_CACHE_MAX_ENTRIES = 128


@dataclass(frozen=True, slots=True)
class CachedDistanceEntry:
    result: DistanceMatrixResult
    stored_at: datetime


class DistanceCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_DISTANCE_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_DISTANCE_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedDistanceEntry] = {}
        self._lock = Lock()

    @staticmethod
    def cache_key(request: DistanceMatrixRequest) -> str:
        origin_part = "|".join(
            f"{point.name}:{point.latitude:.6f},{point.longitude:.6f}"
            for point in request.origins
        )
        destination_part = "|".join(
            f"{point.name}:{point.latitude:.6f},{point.longitude:.6f}"
            for point in request.destinations
        )
        return f"{origin_part}>>{destination_part}>>{request.travel_mode.value}"

    def get(self, key: str) -> CachedDistanceEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: DistanceMatrixResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedDistanceEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
