"""Authenticated agent planning API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_agent_run_service, get_current_user
from app.api.schemas import (
    AgentRunCreateRequest,
    AgentRunMessageRequest,
    AgentRunResponse,
    agent_run_outcome_to_response,
)
from app.auth.exceptions import AuthorizationError, ResourceNotFoundError
from app.core.current_user import CurrentUser
from app.services.agent_runs import AgentRunService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_run(
    payload: AgentRunCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    agent_run_service: Annotated[AgentRunService, Depends(get_agent_run_service)],
) -> AgentRunResponse:
    """Start a new trip planning run from natural-language input."""
    outcome = agent_run_service.start_run(current_user.id, payload.message)
    return agent_run_outcome_to_response(outcome)


@router.post("/runs/{run_id}/messages", response_model=AgentRunResponse)
async def submit_agent_run_message(
    run_id: str,
    payload: AgentRunMessageRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    agent_run_service: Annotated[AgentRunService, Depends(get_agent_run_service)],
) -> AgentRunResponse:
    """Submit clarification text and resume an existing planning run."""
    try:
        outcome = agent_run_service.resume_run(
            current_user.id,
            run_id,
            payload.message,
        )
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

    return agent_run_outcome_to_response(outcome)
