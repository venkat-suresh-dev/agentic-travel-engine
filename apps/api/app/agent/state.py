"""LangGraph state definitions for the trip planning agent."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypedDict

from mcp_tools.currency.schemas import CurrencyConversionResult, CurrencyToolMetadata
from mcp_tools.distance.schemas import DistanceMatrixResult, DistanceToolMetadata
from mcp_tools.flights.schemas import FlightSearchResult, FlightToolMetadata
from mcp_tools.hotels.schemas import HotelSearchResult, HotelToolMetadata
from mcp_tools.places.schemas import (
    AttractionSearchResult,
    PlacesToolMetadata,
    RestaurantSearchResult,
)
from mcp_tools.weather.schemas import WeatherForecastResult, WeatherToolMetadata

from app.agent.orchestration.schemas import (
    AggregateRunStatus,
    ToolOrchestrationSummary,
)
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult


def _merge_tool_orchestration(
    left: list[dict[str, object]] | None,
    right: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    return (left or []) + (right or [])


class GraphStatus(StrEnum):
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    AWAITING_USER = "awaiting_user"
    COMPLETE = "complete"


class ConversationMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict, total=False):
    """Shared LangGraph state for the extract → validate → ask_user loop."""

    user_request: str
    user_clarification: str | None
    messages: list[ConversationMessage]
    trip_request: dict[str, object] | None
    validation: dict[str, object] | None
    clarification: dict[str, object] | None
    weather_forecast: dict[str, object] | None
    weather_tool_metadata: dict[str, object] | None
    flight_search: dict[str, object] | None
    flight_tool_metadata: dict[str, object] | None
    hotel_search: dict[str, object] | None
    hotel_tool_metadata: dict[str, object] | None
    distance_matrix: dict[str, object] | None
    distance_tool_metadata: dict[str, object] | None
    restaurant_search: dict[str, object] | None
    restaurant_tool_metadata: dict[str, object] | None
    attraction_search: dict[str, object] | None
    attraction_tool_metadata: dict[str, object] | None
    currency_conversion: dict[str, object] | None
    currency_tool_metadata: dict[str, object] | None
    tool_orchestration: Annotated[list[dict[str, object]], _merge_tool_orchestration]
    tool_fan_out_started_at: str | None
    aggregate_run_status: str | None
    tool_orchestration_summary: dict[str, object] | None
    status: str


class AgentInput(TypedDict, total=False):
    """External graph input for initial and resumed invocations."""

    user_request: str
    user_clarification: str | None
    messages: list[ConversationMessage]


def trip_request_from_state(state: AgentState) -> TripRequest | None:
    raw = state.get("trip_request")
    if raw is None:
        return None
    return TripRequest.model_validate(raw)


def validation_from_state(state: AgentState) -> ValidationResult | None:
    raw = state.get("validation")
    if raw is None:
        return None
    return ValidationResult.model_validate(raw)


def clarification_from_state(state: AgentState) -> ClarificationRequest | None:
    raw = state.get("clarification")
    if raw is None:
        return None
    return ClarificationRequest.model_validate(raw)


def weather_forecast_from_state(state: AgentState) -> WeatherForecastResult | None:
    raw = state.get("weather_forecast")
    if raw is None:
        return None
    return WeatherForecastResult.model_validate(raw)


def weather_metadata_from_state(state: AgentState) -> WeatherToolMetadata | None:
    raw = state.get("weather_tool_metadata")
    if raw is None:
        return None
    return WeatherToolMetadata.model_validate(raw)


def flight_search_from_state(state: AgentState) -> FlightSearchResult | None:
    raw = state.get("flight_search")
    if raw is None:
        return None
    return FlightSearchResult.model_validate(raw)


def flight_metadata_from_state(state: AgentState) -> FlightToolMetadata | None:
    raw = state.get("flight_tool_metadata")
    if raw is None:
        return None
    return FlightToolMetadata.model_validate(raw)


def hotel_search_from_state(state: AgentState) -> HotelSearchResult | None:
    raw = state.get("hotel_search")
    if raw is None:
        return None
    return HotelSearchResult.model_validate(raw)


def hotel_metadata_from_state(state: AgentState) -> HotelToolMetadata | None:
    raw = state.get("hotel_tool_metadata")
    if raw is None:
        return None
    return HotelToolMetadata.model_validate(raw)


def distance_matrix_from_state(state: AgentState) -> DistanceMatrixResult | None:
    raw = state.get("distance_matrix")
    if raw is None:
        return None
    return DistanceMatrixResult.model_validate(raw)


def distance_metadata_from_state(state: AgentState) -> DistanceToolMetadata | None:
    raw = state.get("distance_tool_metadata")
    if raw is None:
        return None
    return DistanceToolMetadata.model_validate(raw)


def restaurant_search_from_state(state: AgentState) -> RestaurantSearchResult | None:
    raw = state.get("restaurant_search")
    if raw is None:
        return None
    return RestaurantSearchResult.model_validate(raw)


def restaurant_metadata_from_state(state: AgentState) -> PlacesToolMetadata | None:
    raw = state.get("restaurant_tool_metadata")
    if raw is None:
        return None
    return PlacesToolMetadata.model_validate(raw)


def attraction_search_from_state(state: AgentState) -> AttractionSearchResult | None:
    raw = state.get("attraction_search")
    if raw is None:
        return None
    return AttractionSearchResult.model_validate(raw)


def attraction_metadata_from_state(state: AgentState) -> PlacesToolMetadata | None:
    raw = state.get("attraction_tool_metadata")
    if raw is None:
        return None
    return PlacesToolMetadata.model_validate(raw)


def currency_conversion_from_state(
    state: AgentState,
) -> CurrencyConversionResult | None:
    raw = state.get("currency_conversion")
    if raw is None:
        return None
    return CurrencyConversionResult.model_validate(raw)


def currency_metadata_from_state(state: AgentState) -> CurrencyToolMetadata | None:
    raw = state.get("currency_tool_metadata")
    if raw is None:
        return None
    return CurrencyToolMetadata.model_validate(raw)


def aggregate_run_status_from_state(
    state: AgentState,
) -> AggregateRunStatus | None:
    raw = state.get("aggregate_run_status")
    if raw is None:
        return None
    return AggregateRunStatus(raw)


def orchestration_summary_from_state(
    state: AgentState,
) -> ToolOrchestrationSummary | None:
    raw = state.get("tool_orchestration_summary")
    if raw is None:
        return None
    return ToolOrchestrationSummary.model_validate(raw)
