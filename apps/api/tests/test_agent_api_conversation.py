"""Phase 6B API conversation lifecycle tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.agent.service import TripPlannerAgentService
from app.api.deps import get_agent_run_service, get_auth_verifier
from app.api.schemas import AgentRunResponse
from app.auth.types import AuthenticatedIdentity
from app.db.session import get_db
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.critic.engine import ItineraryCritic
from app.itinerary.critic.schemas import (
    CriticIssue,
    CriticIssueCode,
    CriticIssueSeverity,
    CriticResult,
)
from app.llm.exceptions import LLMProviderError
from app.llm.types import StructuredLLMResult
from app.main import create_app
from app.modification.schemas import TripModificationRequest
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
from tests.test_agent_api import (
    COMPLETE_REQUEST,
    FULL_CLARIFICATION,
    INCOMPLETE_REQUEST,
)
from tests.test_auth import FakeAuthVerifier


class FailModificationOnlyAdapter(FakeLLMAdapter):
    """Fail only modification extraction while preserving planning behavior."""

    def generate_structured(self, **kwargs: Any) -> StructuredLLMResult[Any]:
        response_model = kwargs.get("response_model")
        if response_model is TripModificationRequest:
            raise LLMProviderError("simulated modification extraction failure")
        return super().generate_structured(**kwargs)


FORBIDDEN_RESPONSE_KEYS = {
    "state",
    "messages",
    "modification_scope",
    "modification_request",
    "refresh_plan",
    "previous_itinerary",
    "itinerary_draft",
    "itinerary_candidate",
    "tool_orchestration",
}


@pytest.fixture
def agent_registry() -> AgentRunRegistry:
    return AgentRunRegistry()


@pytest.fixture
def agent_service(
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
        llm_adapter=FakeLLMAdapter.from_stub(),
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
        itinerary_composer=FakeItineraryComposer(),
    )


@pytest.fixture
def agent_run_service(
    agent_service: TripPlannerAgentService,
    agent_registry: AgentRunRegistry,
) -> AgentRunService:
    return AgentRunService(agent_service, agent_registry)


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


async def _register_user(
    db_session: AsyncSession,
    agent_app: FastAPI,
    *,
    external_auth_id: str,
    email: str,
) -> dict[str, str]:
    identity = AuthenticatedIdentity(
        external_auth_id=external_auth_id,
        email=email,
        display_name=email.split("@", 1)[0],
    )
    await resolve_or_create_user(db_session, identity)
    agent_app.dependency_overrides[get_auth_verifier] = lambda: FakeAuthVerifier(
        identity
    )
    return {"Authorization": "Bearer test-token"}


def _assert_response_contract(body: dict[str, object]) -> None:
    AgentRunResponse.model_validate(body)
    for key in FORBIDDEN_RESPONSE_KEYS:
        assert key not in body
    assert "traceback" not in str(body).lower()
    operation = body["operation"]
    assert isinstance(operation, dict)
    assert operation["operation_type"] in {
        "initial_plan",
        "clarification",
        "modification",
    }


@pytest.mark.asyncio
async def test_initial_plan_exposes_operation_metadata(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-initial",
        email="conv-initial@example.com",
    )
    response = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    body = response.json()
    assert response.status_code == 201
    _assert_response_contract(body)
    assert body["operation"]["operation_type"] == "initial_plan"
    assert body["operation"]["status"] == "complete"
    assert body["itinerary"] is not None
    assert body["budget"] is not None
    assert body["tool_availability"] is not None


@pytest.mark.asyncio
async def test_clarification_operation_type_and_preserves_fields(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-clarify",
        email="conv-clarify@example.com",
    )
    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]
    assert initial.json()["operation"]["operation_type"] == "initial_plan"
    assert initial.json()["operation"]["status"] == "needs_clarification"

    resumed = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": FULL_CLARIFICATION},
        headers=headers,
    )
    body = resumed.json()
    _assert_response_contract(body)
    assert body["operation"]["operation_type"] == "clarification"
    assert body["operation"]["status"] == "complete"
    assert body["run_id"] == run_id
    assert body["trip_request"]["destination"] == "Dubai"
    assert body["trip_request"]["travelers"] == 2
    assert body["itinerary"] is not None


@pytest.mark.asyncio
async def test_clarification_not_confused_with_modification(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-not-mod",
        email="conv-not-mod@example.com",
    )
    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": INCOMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]

    resumed = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": FULL_CLARIFICATION},
        headers=headers,
    )
    assert resumed.json()["operation"]["operation_type"] == "clarification"
    assert resumed.json()["operation"]["operation_type"] != "modification"


@pytest.mark.asyncio
async def test_completed_plan_modification_returns_operation_metadata(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-mod",
        email="conv-mod@example.com",
    )
    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]
    before_days = initial.json()["itinerary"]["days"]

    modified = await agent_client.post(
        f"/api/agent/runs/{run_id}/messages",
        json={"message": "Make day 2 more relaxed."},
        headers=headers,
    )
    body = modified.json()
    _assert_response_contract(body)
    assert body["status"] == "complete"
    assert body["operation"]["operation_type"] == "modification"
    assert body["operation"]["status"] == "complete"
    assert 2 in body["operation"]["affected_days"]
    assert body["operation"]["budget_changed"] is True
    assert body["itinerary"] is not None
    assert body["itinerary"]["days"][0] == before_days[0]
    assert body["itinerary"]["days"][2:] == before_days[2:]


@pytest.mark.asyncio
async def test_modification_extraction_failure_preserves_itinerary(
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
    db_session: AsyncSession,
) -> None:
    registry = AgentRunRegistry()
    planner = TripPlannerAgentService(
        llm_adapter=FailModificationOnlyAdapter.from_stub(),
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
        itinerary_composer=FakeItineraryComposer(),
    )
    service = AgentRunService(planner, registry)
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_run_service] = lambda: service

    headers = await _register_user(
        db_session,
        app,
        external_auth_id="conv-mod-extract-fail",
        email="conv-mod-extract-fail@example.com",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.post(
            "/api/agent/runs",
            json={"message": COMPLETE_REQUEST},
            headers=headers,
        )
        assert initial.status_code == 201
        run_id = initial.json()["run_id"]
        before_itinerary = initial.json()["itinerary"]

        resumed = await client.post(
            f"/api/agent/runs/{run_id}/messages",
            json={"message": "Make day 2 more relaxed."},
            headers=headers,
        )

    body = resumed.json()
    assert body["status"] == "failed"
    assert body["operation"]["operation_type"] == "modification"
    assert body["itinerary"] == before_itinerary
    assert body["error"] == "Requirement extraction failed. Please try again."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_modification_critic_retry_exhaustion_preserves_itinerary(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-mod-critic",
        email="conv-mod-critic@example.com",
    )
    initial = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    run_id = initial.json()["run_id"]
    before_itinerary = initial.json()["itinerary"]

    def always_invalid(
        self: ItineraryCritic,
        *,
        candidate: object,
        itinerary: object,
        context: object,
        catalog: object,
    ) -> CriticResult:
        return CriticResult(
            valid=False,
            issues=[
                CriticIssue(
                    code=CriticIssueCode.UNSUPPORTED_ITEM,
                    severity=CriticIssueSeverity.ERROR,
                    message="simulated critic rejection",
                )
            ],
            retryable=True,
        )

    with patch.object(ItineraryCritic, "critique", always_invalid):
        modified = await agent_client.post(
            f"/api/agent/runs/{run_id}/messages",
            json={"message": "Make day 2 more relaxed."},
            headers=headers,
        )

    body = modified.json()
    _assert_response_contract(body)
    assert body["status"] == "failed"
    assert body["operation"]["operation_type"] == "modification"
    assert body["modification_failure"] is not None
    assert body["modification_failure"]["preserved_itinerary"] is True
    assert body["itinerary"] == before_itinerary
    assert "could not be applied" in (body["operation"]["summary"] or "")


@pytest.mark.asyncio
async def test_response_never_exposes_internal_graph_state(
    agent_app: FastAPI,
    agent_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _register_user(
        db_session,
        agent_app,
        external_auth_id="conv-contract",
        email="conv-contract@example.com",
    )
    response = await agent_client.post(
        "/api/agent/runs",
        json={"message": COMPLETE_REQUEST},
        headers=headers,
    )
    _assert_response_contract(response.json())
