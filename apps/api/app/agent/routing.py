"""Graph routing helpers."""

from __future__ import annotations

from typing import Literal

from app.agent.state import AgentState, validation_from_state

RouteAfterValidation = Literal["fetch_weather", "ask_user"]


def route_after_validation(state: AgentState) -> RouteAfterValidation:
    """Route complete requirements to weather fetch; otherwise ask for clarification."""
    validation = validation_from_state(state)
    if validation is not None and validation.is_complete:
        return "fetch_weather"
    return "ask_user"
