"""Extract structured trip requirements from user input."""

from __future__ import annotations

from app.agent.nodes.extract_stub import extract_from_text
from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.domain.trip_request import TripRequest


def extract_requirements(state: AgentState) -> AgentState:
    """Extract or merge structured requirements from the latest user text."""
    existing = trip_request_from_state(state)
    source_text = state.get("user_clarification") or state.get("user_request", "")
    if not source_text:
        trip_request = existing or TripRequest()
    else:
        trip_request = extract_from_text(source_text, existing=existing)

    messages = list(state.get("messages", []))
    if source_text:
        role = "user_clarification" if state.get("user_clarification") else "user"
        messages.append({"role": role, "content": source_text})

    return {
        "trip_request": trip_request.model_dump(mode="json"),
        "messages": messages,
        "status": GraphStatus.VALIDATING.value,
        "clarification": None,
    }
