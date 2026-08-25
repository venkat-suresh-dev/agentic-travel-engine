"""In-process pub/sub and bounded buffering for agent run SSE events."""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentRunEventType(StrEnum):
    """Stable SSE event types for agent execution."""

    RUN_STARTED = "run_started"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    PARALLEL_GROUP_STARTED = "parallel_group_started"
    PARALLEL_GROUP_COMPLETED = "parallel_group_completed"
    RUN_STATUS_CHANGED = "run_status_changed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    HEARTBEAT = "heartbeat"


class AgentRunEvent(BaseModel):
    """Structured execution event emitted over SSE."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    type: AgentRunEventType
    timestamp: str
    node_name: str | None = None
    tool_name: str | None = None
    status: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


TOOL_NODE_NAMES: frozenset[str] = frozenset(
    {
        "fetch_weather",
        "search_flights",
        "search_hotels",
        "get_distance_matrix",
        "search_restaurants",
        "search_attractions",
        "convert_currency",
    }
)

TOOL_DISPLAY_NAMES: dict[str, str] = {
    "fetch_weather": "weather",
    "search_flights": "flights",
    "search_hotels": "hotels",
    "get_distance_matrix": "distance",
    "search_restaurants": "restaurants",
    "search_attractions": "attractions",
    "convert_currency": "currency",
}

TRACKED_NODE_NAMES: frozenset[str] = frozenset(
    {
        "extract_requirements",
        "extract_modification",
        "validate_requirements",
        "resolve_modification_scope",
        "retrieve_context",
        "ask_user",
        "fetch_weather",
        "search_flights",
        "search_hotels",
        "get_distance_matrix",
        "search_restaurants",
        "search_attractions",
        "aggregate_independent_tools",
        "convert_currency",
        "compute_budget",
        "build_itinerary",
        "critic_validate",
        "apply_modification",
        "recompute_modification_budget",
        "finalize_run",
        "finalize_failure",
        "finalize_modification_failure",
    }
)

DEFAULT_BUFFER_SIZE = 500
HEARTBEAT_INTERVAL_SECONDS = 15.0


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_event(
    *,
    run_id: str,
    event_type: AgentRunEventType,
    node_name: str | None = None,
    tool_name: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentRunEvent:
    return AgentRunEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        type=event_type,
        timestamp=_utc_now_iso(),
        node_name=node_name,
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )


@dataclass
class _RunChannel:
    """Bounded event history and live subscriber queues for one run."""

    run_id: str
    buffer_size: int
    events: deque[AgentRunEvent] = field(init=False)
    subscribers: list[asyncio.Queue[AgentRunEvent | None]] = field(
        default_factory=list,
    )
    completed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.events = deque(maxlen=self.buffer_size)

    def publish(self, event: AgentRunEvent) -> None:
        with self.lock:
            self.events.append(event)
            for queue in list(self.subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def mark_completed(self) -> None:
        with self.lock:
            self.completed = True
            for queue in list(self.subscribers):
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    def subscribe(self) -> asyncio.Queue[AgentRunEvent | None]:
        queue: asyncio.Queue[AgentRunEvent | None] = asyncio.Queue(maxsize=100)
        with self.lock:
            for event in self.events:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    break
            self.subscribers.append(queue)
            if self.completed:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
        return queue

    def unsubscribe(self, queue: asyncio.Queue[AgentRunEvent | None]) -> None:
        with self.lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)


class AgentRunEventPublisher:
    """Publishes execution events for a single run."""

    def __init__(self, channel: _RunChannel) -> None:
        self._channel = channel
        self._run_id = channel.run_id
        self._run_started_at = time.perf_counter()
        self._node_started_at: dict[str, float] = {}
        self._tool_started_at: dict[str, float] = {}
        self._parallel_active = False
        self._seen_event_ids: set[str] = set()

    @property
    def run_id(self) -> str:
        return self._run_id

    def publish(self, event: AgentRunEvent) -> None:
        if event.event_id in self._seen_event_ids:
            return
        self._seen_event_ids.add(event.event_id)
        self._channel.publish(event)

    def run_started(self, *, operation_type: str | None = None) -> None:
        metadata: dict[str, Any] = {}
        if operation_type:
            metadata["operation_type"] = operation_type
        self.publish(
            new_event(
                run_id=self._run_id,
                event_type=AgentRunEventType.RUN_STARTED,
                metadata=metadata,
            ),
        )

    def node_started(self, node_name: str) -> None:
        if node_name not in TRACKED_NODE_NAMES:
            return
        self._node_started_at[node_name] = time.perf_counter()
        if node_name in TOOL_NODE_NAMES:
            tool_name = TOOL_DISPLAY_NAMES.get(node_name, node_name)
            if not self._parallel_active:
                self._parallel_active = True
                self.publish(
                    new_event(
                        run_id=self._run_id,
                        event_type=AgentRunEventType.PARALLEL_GROUP_STARTED,
                        metadata={"tools": list(TOOL_DISPLAY_NAMES.values())},
                    ),
                )
            self.publish(
                new_event(
                    run_id=self._run_id,
                    event_type=AgentRunEventType.TOOL_STARTED,
                    node_name=node_name,
                    tool_name=tool_name,
                    status="running",
                ),
            )
        else:
            self.publish(
                new_event(
                    run_id=self._run_id,
                    event_type=AgentRunEventType.NODE_STARTED,
                    node_name=node_name,
                    status="running",
                ),
            )

    def node_completed(
        self,
        node_name: str,
        *,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        if node_name not in TRACKED_NODE_NAMES:
            return
        started = self._node_started_at.pop(node_name, None)
        duration_ms = (
            (time.perf_counter() - started) * 1000 if started is not None else None
        )
        metadata: dict[str, Any] = {}
        if error_message:
            metadata["error_message"] = error_message

        if node_name in TOOL_NODE_NAMES:
            tool_name = TOOL_DISPLAY_NAMES.get(node_name, node_name)
            self._tool_started_at.pop(node_name, None)
            self.publish(
                new_event(
                    run_id=self._run_id,
                    event_type=AgentRunEventType.TOOL_COMPLETED,
                    node_name=node_name,
                    tool_name=tool_name,
                    status=status,
                    duration_ms=duration_ms,
                    metadata=metadata,
                ),
            )
        else:
            self.publish(
                new_event(
                    run_id=self._run_id,
                    event_type=AgentRunEventType.NODE_COMPLETED,
                    node_name=node_name,
                    status=status,
                    duration_ms=duration_ms,
                    metadata=metadata,
                ),
            )

        if node_name == "aggregate_independent_tools" and self._parallel_active:
            self._parallel_active = False
            self.publish(
                new_event(
                    run_id=self._run_id,
                    event_type=AgentRunEventType.PARALLEL_GROUP_COMPLETED,
                    node_name=node_name,
                    status=status,
                ),
            )

    def node_failed(self, node_name: str, *, error_message: str) -> None:
        self.node_completed(node_name, status="failed", error_message=error_message)
        self.publish(
            new_event(
                run_id=self._run_id,
                event_type=AgentRunEventType.NODE_FAILED,
                node_name=node_name,
                status="failed",
                metadata={"error_message": error_message},
            ),
        )

    def run_status_changed(self, status: str) -> None:
        self.publish(
            new_event(
                run_id=self._run_id,
                event_type=AgentRunEventType.RUN_STATUS_CHANGED,
                status=status,
            ),
        )

    def run_completed(self, *, summary: dict[str, Any] | None = None) -> None:
        duration_ms = (time.perf_counter() - self._run_started_at) * 1000
        self.publish(
            new_event(
                run_id=self._run_id,
                event_type=AgentRunEventType.RUN_COMPLETED,
                status="complete",
                duration_ms=duration_ms,
                metadata=summary or {},
            ),
        )
        self._channel.mark_completed()

    def run_failed(self, *, message: str) -> None:
        duration_ms = (time.perf_counter() - self._run_started_at) * 1000
        self.publish(
            new_event(
                run_id=self._run_id,
                event_type=AgentRunEventType.RUN_FAILED,
                status="failed",
                duration_ms=duration_ms,
                metadata={"message": message},
            ),
        )
        self._channel.mark_completed()

    def close(self) -> None:
        if not self._channel.completed:
            self._channel.mark_completed()


class AgentRunEventBus:
    """Process-local event bus with bounded per-run buffers."""

    def __init__(self, *, buffer_size: int = DEFAULT_BUFFER_SIZE) -> None:
        self._buffer_size = buffer_size
        self._channels: dict[str, _RunChannel] = {}
        self._lock = threading.Lock()

    def ensure_run(self, run_id: str) -> AgentRunEventPublisher:
        with self._lock:
            channel = self._channels.get(run_id)
            if channel is None:
                channel = _RunChannel(run_id=run_id, buffer_size=self._buffer_size)
                self._channels[run_id] = channel
            return AgentRunEventPublisher(channel)

    def get_publisher(self, run_id: str) -> AgentRunEventPublisher | None:
        with self._lock:
            channel = self._channels.get(run_id)
            if channel is None:
                return None
            return AgentRunEventPublisher(channel)

    def has_run(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._channels

    def replay_events(self, run_id: str) -> list[AgentRunEvent]:
        with self._lock:
            channel = self._channels.get(run_id)
            if channel is None:
                return []
            return list(channel.events)

    def is_completed(self, run_id: str) -> bool:
        with self._lock:
            channel = self._channels.get(run_id)
            return channel.completed if channel is not None else False

    def cleanup_run(self, run_id: str) -> None:
        with self._lock:
            self._channels.pop(run_id, None)

    async def subscribe(self, run_id: str) -> AsyncIterator[AgentRunEvent]:
        with self._lock:
            channel = self._channels.get(run_id)
            if channel is None:
                channel = _RunChannel(run_id=run_id, buffer_size=self._buffer_size)
                self._channels[run_id] = channel
        queue = channel.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )
                except TimeoutError:
                    yield new_event(
                        run_id=run_id,
                        event_type=AgentRunEventType.HEARTBEAT,
                    )
                    continue
                if event is None:
                    break
                yield event
        finally:
            channel.unsubscribe(queue)

    def format_sse(self, event: AgentRunEvent) -> str:
        return f"data: {event.model_dump_json()}\n\n"


def iter_buffered_then_live(
    events: list[AgentRunEvent],
    live: Iterator[AgentRunEvent],
) -> Iterator[AgentRunEvent]:
    yield from events
    yield from live
