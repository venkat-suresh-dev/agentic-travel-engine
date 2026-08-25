"""In-process weather response cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from mcp_tools.weather.schemas import WeatherForecastRequest, WeatherForecastResult

# Forecasts change frequently; 30 minutes balances freshness with provider load.
DEFAULT_WEATHER_CACHE_TTL_SECONDS = 1800
DEFAULT_WEATHER_CACHE_MAX_ENTRIES = 256


@dataclass(frozen=True, slots=True)
class CachedWeatherEntry:
    result: WeatherForecastResult
    stored_at: datetime


class WeatherCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_WEATHER_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_WEATHER_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedWeatherEntry] = {}
        self._lock = Lock()

    @staticmethod
    def cache_key(request: WeatherForecastRequest) -> str:
        return (
            f"{request.location.strip().lower()}|"
            f"{request.start_date.isoformat()}|"
            f"{request.end_date.isoformat()}"
        )

    def get(self, key: str) -> CachedWeatherEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: WeatherForecastResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedWeatherEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
