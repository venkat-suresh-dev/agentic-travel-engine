"""Extract structured trip requirements from user input."""

from __future__ import annotations

import json
from collections.abc import Callable

from app.agent.exceptions import RequirementExtractionError
from app.agent.state import AgentState, GraphStatus, trip_request_from_state
from app.agent.trip_request_merge import merge_trip_requests
from app.domain.trip_request import TripRequest
from app.llm.base import LLMAdapter
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.llm.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_user_prompt


def build_extract_requirements_node(
    llm_adapter: LLMAdapter,
) -> Callable[[AgentState], AgentState]:
    """Create an extract node bound to the provided LLM adapter."""

    def extract_requirements(state: AgentState) -> AgentState:
        """Extract or merge structured requirements from the latest user text."""
        existing = trip_request_from_state(state)
        source_text = state.get("user_clarification") or state.get("user_request", "")
        is_clarification = bool(state.get("user_clarification"))

        if not source_text:
            trip_request = existing or TripRequest()
        else:
            user_prompt = build_extraction_user_prompt(
                user_text=source_text,
                existing_requirements_json=(
                    json.dumps(existing.model_dump(mode="json"), indent=2)
                    if existing is not None
                    else None
                ),
                is_clarification=is_clarification,
            )
            try:
                result = llm_adapter.generate_structured(
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_model=TripRequest,
                )
            except (LLMProviderError, LLMStructuredOutputError) as exc:
                raise RequirementExtractionError(str(exc)) from exc

            extracted = result.data
            trip_request = (
                merge_trip_requests(existing, extracted)
                if existing is not None
                else extracted
            )

        messages = list(state.get("messages", []))
        if source_text:
            role = "user_clarification" if is_clarification else "user"
            messages.append({"role": role, "content": source_text})

        return {
            "trip_request": trip_request.model_dump(mode="json"),
            "messages": messages,
            "status": GraphStatus.VALIDATING.value,
            "clarification": None,
        }

    return extract_requirements
