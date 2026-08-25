"""In-process currency rate cache with TTL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from mcp_tools.currency.schemas import (
    CurrencyConversionRequest,
    CurrencyConversionResult,
)

# Frankfurter/ECB reference rates are published daily; cache for 24 hours to align
# with provider freshness rather than pretending intraday market updates.
DEFAULT_CURRENCY_CACHE_TTL_SECONDS = 86_400
DEFAULT_CURRENCY_CACHE_MAX_ENTRIES = 128


@dataclass(frozen=True, slots=True)
class CachedCurrencyEntry:
    result: CurrencyConversionResult
    stored_at: datetime


class CurrencyCache:
    """Bounded TTL cache replaceable with Redis in production."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_CURRENCY_CACHE_TTL_SECONDS,
        max_entries: int = DEFAULT_CURRENCY_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._entries: dict[str, CachedCurrencyEntry] = {}
        self._lock = Lock()

    @staticmethod
    def cache_key(request: CurrencyConversionRequest) -> str:
        rate_date = request.rate_date.isoformat() if request.rate_date else "latest"
        return (
            f"{request.base_currency}|{request.quote_currency}|"
            f"{request.amount}|{rate_date}"
        )

    def get(self, key: str) -> CachedCurrencyEntry | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not self.is_fresh(entry.stored_at):
                del self._entries[key]
                return None
            return entry

    def set(self, key: str, result: CurrencyConversionResult) -> None:
        with self._lock:
            if len(self._entries) >= self._max_entries:
                oldest_key = min(
                    self._entries,
                    key=lambda item: self._entries[item].stored_at,
                )
                del self._entries[oldest_key]
            self._entries[key] = CachedCurrencyEntry(
                result=result,
                stored_at=datetime.now(UTC),
            )

    def is_fresh(self, stored_at: datetime) -> bool:
        return datetime.now(UTC) - stored_at <= self._ttl
