"""In-process flight search cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from mcp_tools.flights.schemas import FlightSearchRequest, FlightSearchResult

# Flight pricing changes quickly; 5 minutes balances freshness with provider load.
DEFAULT_FLIGHT_CACHE_TTL_SECONDS = 300
DEFAULT_FLIGHT_CACHE_MAX_ENTRIES = 128


@dataclass(frozen=True, slots=True)
class CachedFlightEntry:
    result: FlightSearchResult
    stored_at: datetime


class FlightCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_FLIGHT_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_FLIGHT_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedFlightEntry] = {}
        self._lock = Lock()

    @staticmethod
    def cache_key(request: FlightSearchRequest) -> str:
        return_date = (
            request.return_date.isoformat() if request.return_date else "oneway"
        )
        return (
            f"{request.origin}|{request.destination}|"
            f"{request.departure_date.isoformat()}|{return_date}|"
            f"{request.travelers}|{request.cabin_class.value}|{request.currency}"
        )

    def get(self, key: str) -> CachedFlightEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: FlightSearchResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedFlightEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
