"""Bounded concurrency control for parallel tool orchestration."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock, Semaphore


class ToolConcurrencyLimiter:
    """Limit concurrent tool executions across parallel graph branches."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            msg = "tool concurrency limit must be at least 1"
            raise ValueError(msg)
        self._limit = limit
        self._semaphore = Semaphore(limit)
        self._lock = Lock()
        self._active = 0
        self._max_observed = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def max_observed_concurrency(self) -> int:
        with self._lock:
            return self._max_observed

    @contextmanager
    def acquire(self) -> Generator[None]:
        self._semaphore.acquire()
        with self._lock:
            self._active += 1
            if self._active > self._max_observed:
                self._max_observed = self._active
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()
