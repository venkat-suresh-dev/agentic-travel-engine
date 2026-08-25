"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from app.agent.state import AgentState, validation_from_state

RouteAfterValidation = Literal["ask_user", "__end__"]


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route to ask_user when requirements are incomplete, otherwise end the graph."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return "__end__"
    return "ask_user"
