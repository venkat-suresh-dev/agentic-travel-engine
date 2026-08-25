"""Bridge itinerary building from LangGraph agent state."""

from __future__ import annotations

from app.agent.state import (
    AgentState,
    attraction_search_from_state,
    budget_result_from_state,
    currency_conversion_from_state,
    distance_matrix_from_state,
    flight_search_from_state,
    hotel_search_from_state,
    restaurant_search_from_state,
    trip_request_from_state,
    weather_forecast_from_state,
)
from app.itinerary.builder import ItineraryBuilder
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import (
    ItineraryBuildResult,
    ItineraryValidationIssue,
    ItineraryValidationResult,
)
from app.rag.schemas import RetrievedContext


def build_itinerary_context_from_state(
    state: AgentState,
) -> ItineraryBuildContext | None:
    trip_request = trip_request_from_state(state)
    budget_result = budget_result_from_state(state)
    if trip_request is None or budget_result is None:
        return None
    retrieved_raw = state.get("retrieved_context")
    retrieved = (
        RetrievedContext.model_validate(retrieved_raw)
        if retrieved_raw is not None
        else None
    )
    return ItineraryBuildContext(
        trip_request=trip_request,
        weather_forecast=weather_forecast_from_state(state),
        flight_search=flight_search_from_state(state),
        hotel_search=hotel_search_from_state(state),
        distance_matrix=distance_matrix_from_state(state),
        restaurant_search=restaurant_search_from_state(state),
        attraction_search=attraction_search_from_state(state),
        currency_conversion=currency_conversion_from_state(state),
        budget_result=budget_result,
        retrieved_context=retrieved,
    )


def build_itinerary_from_state(
    state: AgentState,
    *,
    builder: ItineraryBuilder | None = None,
    composer: ItineraryComposer | None = None,
) -> ItineraryBuildResult:
    itinerary_builder = builder or ItineraryBuilder(composer=composer)
    context = build_itinerary_context_from_state(state)
    if context is None:
        return ItineraryBuildResult(
            success=False,
            validation=ItineraryValidationResult(
                is_valid=False,
                issues=[
                    ItineraryValidationIssue(
                        code="missing_context",
                        message="trip request and budget result are required",
                    )
                ],
            ),
        )
    try:
        return itinerary_builder.build_from_context(context)
    except ValueError as exc:
        return ItineraryBuildResult(
            success=False,
            validation=ItineraryValidationResult(
                is_valid=False,
                issues=[
                    ItineraryValidationIssue(
                        code="composition_failed",
                        message=str(exc),
                    )
                ],
            ),
        )
