"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Send

from app.agent.orchestration.fan_out import fan_out_independent_tools
from app.agent.state import AgentState, validation_from_state

RouteAfterValidation = list[Send] | Literal["ask_user"]


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route complete requirements to parallel tool fan-out; otherwise ask user."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return fan_out_independent_tools(state)
    return "ask_user"
