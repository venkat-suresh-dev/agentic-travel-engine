"""FastAPI dependencies."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from mcp_tools.weather.cache import WeatherCache
from mcp_tools.weather.geocoding.open_meteo import OpenMeteoGeocodingProvider
from mcp_tools.weather.providers.open_meteo import OpenMeteoWeatherProvider
from mcp_tools.weather.service import WeatherService
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.service import TripPlannerAgentService
from app.auth.clerk import AuthVerifier, build_auth_verifier
from app.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
)
from app.core.config import settings
from app.core.current_user import CurrentUser
from app.db.models.trip import Trip
from app.db.session import get_db
from app.llm.factory import build_llm_adapter
from app.services.agent_runs import AgentRunRegistry, AgentRunService
from app.services.ownership import get_owned_trip as load_owned_trip
from app.services.users import resolve_or_create_user
from app.tools.weather import WeatherTool


@lru_cache
def get_auth_verifier() -> AuthVerifier:
    return build_auth_verifier(settings)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_verifier: Annotated[AuthVerifier, Depends(get_auth_verifier)],
) -> CurrentUser:
    try:
        identity = await auth_verifier.verify_request(request)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await resolve_or_create_user(db, identity)
    return CurrentUser.from_user(user)


async def get_owned_trip(
    trip_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Trip:
    try:
        return await load_owned_trip(db, trip_id=trip_id, current_user=current_user)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@lru_cache
def get_agent_run_registry() -> AgentRunRegistry:
    return AgentRunRegistry()


@lru_cache
def get_weather_tool() -> WeatherTool:
    timeout_seconds = settings.weather_request_timeout_seconds
    service = WeatherService(
        geocoding_provider=OpenMeteoGeocodingProvider(
            timeout_seconds=timeout_seconds,
        ),
        weather_provider=OpenMeteoWeatherProvider(
            timeout_seconds=timeout_seconds,
        ),
        cache=WeatherCache(ttl_seconds=settings.weather_cache_ttl_seconds),
    )
    return WeatherTool(service)


@lru_cache
def get_trip_planner_agent_service() -> TripPlannerAgentService:
    return TripPlannerAgentService(
        llm_adapter=build_llm_adapter(),
        weather_tool=get_weather_tool(),
    )


def get_agent_run_service(
    registry: Annotated[AgentRunRegistry, Depends(get_agent_run_registry)],
    agent_service: Annotated[
        TripPlannerAgentService,
        Depends(get_trip_planner_agent_service),
    ],
) -> AgentRunService:
    return AgentRunService(agent_service, registry)
