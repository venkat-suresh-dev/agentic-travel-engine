"""Integration tests for agent run SSE streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from app.agent.service import TripPlannerAgentService
from app.api.deps import get_agent_run_service, get_auth_verifier
from app.auth.exceptions import AuthenticationError
from app.auth.types import AuthenticatedIdentity
from app.db.session import get_db
from app.main import create_app
from app.services.agent_run_events import AgentRunEventBus, AgentRunEventType
from app.services.agent_runs import AgentRunRegistry, AgentRunService
from app.services.users import resolve_or_create_user
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fakes.distance_providers import FakeLocationResolver
from tests.fakes.flights_providers import FakeAirportCodeResolver
from tests.fakes.hotels_providers import FakeCityCodeResolver
from tests.fakes.llm import FakeLLMAdapter
from tests.test_auth import FakeAuthVerifier

COMPLETE_REQUEST = (
    "Plan a 5-day trip to Dubai for 2 people under ₹1,50,000, departing from Mumbai."
)


@pytest.fixture
def agent_registry() -> AgentRunRegistry:
    return AgentRunRegistry()


@pytest.fixture
def event_bus() -> AgentRunEventBus:
    return AgentRunEventBus(buffer_size=100)


@pytest.fixture
def fake_adapter() -> FakeLLMAdapter:
    return FakeLLMAdapter.from_stub()


@pytest.fixture
def agent_service(
    fake_adapter: FakeLLMAdapter,
    fake_weather_tool: WeatherTool,
    fake_flight_tool: FlightTool,
    fake_airport_resolver: FakeAirportCodeResolver,
    fake_hotel_tool: HotelTool,
    fake_city_resolver: FakeCityCodeResolver,
    fake_distance_tool: DistanceTool,
    fake_location_resolver: FakeLocationResolver,
    fake_restaurant_tool: RestaurantTool,
    fake_attraction_tool: AttractionTool,
    fake_currency_tool: CurrencyTool,
) -> TripPlannerAgentService:
    return TripPlannerAgentService(
        llm_adapter=fake_adapter,
        checkpointer=InMemorySaver(),
        weather_tool=fake_weather_tool,
        flight_tool=fake_flight_tool,
        airport_resolver=fake_airport_resolver,
        hotel_tool=fake_hotel_tool,
        city_resolver=fake_city_resolver,
        distance_tool=fake_distance_tool,
        location_resolver=fake_location_resolver,
        restaurant_tool=fake_restaurant_tool,
        attraction_tool=fake_attraction_tool,
        currency_tool=fake_currency_tool,
    )


@pytest.fixture
def agent_run_service(
    agent_service: TripPlannerAgentService,
    agent_registry: AgentRunRegistry,
    event_bus: AgentRunEventBus,
) -> AgentRunService:
    return AgentRunService(agent_service, agent_registry, event_bus)


@pytest.fixture
def agent_app(
    db_session: AsyncSession,
    agent_run_service: AgentRunService,
) -> Generator[FastAPI]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_run_service] = lambda: agent_run_service
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def agent_client(agent_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=agent_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _set_verifier(
    agent_app: FastAPI,
    identity: AuthenticatedIdentity | None = None,
    *,
    error: AuthenticationError | None = None,
) -> None:
    agent_app.dependency_overrides[get_auth_verifier] = lambda: FakeAuthVerifier(
        identity,
        error=error,
    )


async def _setup_user(
    agent_app: FastAPI,
    db_session: AsyncSession,
    *,
    external_id: str,
    email: str,
) -> dict[str, str]:
    identity = AuthenticatedIdentity(
        external_auth_id=external_id,
        email=email,
        display_name="SSE User",
    )
    await resolve_or_create_user(db_session, identity)
    _set_verifier(agent_app, identity)
    return {"Authorization": "Bearer test-token"}


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.mark.asyncio
async def test_stream_requires_authentication(
    agent_app: FastAPI,
    agent_client: AsyncClient,
) -> None:
    _set_verifier(agent_app, error=AuthenticationError("missing token"))

    response = await agent_client.get("/api/agent/runs/some-run/stream")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stream_unknown_run_returns_404(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _setup_user(
        agent_app,
        db_session,
        external_id="sse-unknown",
        email="sse-unknown@example.com",
    )

    response = await agent_client.get(
        "/api/agent/runs/missing-run/stream", headers=headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_emits_events_for_complete_run(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _setup_user(
        agent_app,
        db_session,
        external_id="sse-complete",
        email="sse-complete@example.com",
    )

    create_response = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    stream_response = await agent_client.get(
        f"/api/agent/runs/{run_id}/stream",
        headers=headers,
    )
    assert stream_response.status_code == 200
    assert stream_response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(stream_response.text)
    event_types = [event["type"] for event in events]
    assert AgentRunEventType.RUN_STARTED.value in event_types
    assert AgentRunEventType.RUN_COMPLETED.value in event_types
    assert any(
        event["type"] == AgentRunEventType.TOOL_COMPLETED.value for event in events
    )
    assert events[-1]["type"] == AgentRunEventType.RUN_COMPLETED.value


@pytest.mark.asyncio
async def test_stream_enforces_ownership(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await _setup_user(
        agent_app,
        db_session,
        external_id="sse-owner",
        email="sse-owner@example.com",
    )

    create_response = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=owner_headers,
    )
    run_id = create_response.json()["run_id"]

    other_headers = await _setup_user(
        agent_app,
        db_session,
        external_id="sse-other",
        email="sse-other@example.com",
    )

    response = await agent_client.get(
        f"/api/agent/runs/{run_id}/stream",
        headers=other_headers,
    )
    assert response.status_code == 403


def test_event_bus_bounded_buffer() -> None:
    bus = AgentRunEventBus(buffer_size=3)
    publisher = bus.ensure_run("run-1")
    for _ in range(5):
        publisher.node_started("extract_requirements")
    replay = bus.replay_events("run-1")
    assert len(replay) == 3
