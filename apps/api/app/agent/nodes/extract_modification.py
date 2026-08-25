"""Extract structured trip modification requests from follow-up messages."""

from __future__ import annotations

import json
from collections.abc import Callable

from app.agent.exceptions import RequirementExtractionError
from app.agent.state import (
    AgentState,
    GraphStatus,
    itinerary_from_state,
    trip_request_from_state,
)
from app.agent.trip_request_merge import merge_trip_requests
from app.domain.trip_request import TripRequest
from app.llm.base import LLMAdapter
from app.llm.exceptions import LLMProviderError, LLMStructuredOutputError
from app.llm.prompts import (
    MODIFICATION_SYSTEM_PROMPT,
    build_modification_user_prompt,
)
from app.modification.schemas import (
    ModificationIntent,
    ModificationStatus,
    TripModificationRequest,
)


def build_extract_modification_node(
    llm_adapter: LLMAdapter,
) -> Callable[[AgentState], AgentState]:
    def extract_modification(state: AgentState) -> AgentState:
        previous = itinerary_from_state(state)
        if previous is None:
            msg = "approved itinerary is required for modification extraction"
            raise RequirementExtractionError(msg)

        source_text = state.get("user_clarification") or ""
        user_prompt = build_modification_user_prompt(
            user_text=source_text,
            itinerary_json=json.dumps(previous.model_dump(mode="json"), indent=2),
        )
        try:
            result = llm_adapter.generate_structured(
                system_prompt=MODIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=TripModificationRequest,
            )
        except (LLMProviderError, LLMStructuredOutputError) as exc:
            raise RequirementExtractionError(str(exc)) from exc

        modification = result.data.model_copy(update={"raw_message": source_text})
        messages = list(state.get("messages", []))
        if source_text:
            messages.append({"role": "user_modification", "content": source_text})

        trip_request = trip_request_from_state(state)
        updated_trip_request = trip_request
        if trip_request is not None and modification.intent in {
            ModificationIntent.CHANGE_PACE,
            ModificationIntent.CHANGE_PREFERENCE,
        }:
            extracted = TripRequest(preferences=_preference_updates(source_text))
            updated_trip_request = merge_trip_requests(trip_request, extracted)

        return {
            "modification_request": modification.model_dump(mode="json"),
            "modification_status": ModificationStatus.IN_PROGRESS.value,
            "previous_itinerary": previous.model_dump(mode="json"),
            "trip_request": (
                updated_trip_request.model_dump(mode="json")
                if updated_trip_request is not None
                else None
            ),
            "messages": messages,
            "status": GraphStatus.VALIDATING.value,
            "itinerary_attempt": 0,
            "critic_result": None,
            "critic_issues": [],
            "planning_failed": False,
            "planning_failure": None,
        }

    return extract_modification


def _preference_updates(source_text: str) -> list[str]:
    preferences: list[str] = []
    lowered = source_text.lower()
    if "relaxed pace" in lowered or "relaxed" in lowered:
        preferences.append("relaxed pace")
    if "vegetarian" in lowered:
        preferences.append("vegetarian food")
    return preferences
