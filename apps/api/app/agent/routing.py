"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.agent.orchestration.fan_out import fan_out_independent_tools
from app.agent.state import AgentState, validation_from_state

RouteAfterValidation = Literal["retrieve_context", "ask_user"]
RouteAfterRetrieveContext = list[Send]


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route complete requirements to context retrieval; otherwise ask user."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return "retrieve_context"
    return "ask_user"


def route_after_retrieve_context(state: AgentState) -> RouteAfterRetrieveContext:
    """Fan out independent tools after optional RAG context retrieval."""
    _ = state
    return fan_out_independent_tools(state)
