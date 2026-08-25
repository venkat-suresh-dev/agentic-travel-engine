"""Application service boundary for invoking the trip planner graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from mcp_tools.currency.schemas import CurrencyConversionResult, CurrencyToolMetadata
from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.distance.schemas import DistanceMatrixResult, DistanceToolMetadata
from mcp_tools.flights.airports.base import AirportCodeResolver
from mcp_tools.flights.schemas import FlightSearchResult, FlightToolMetadata
from mcp_tools.hotels.locations.base import CityCodeResolver
from mcp_tools.hotels.schemas import HotelSearchResult, HotelToolMetadata
from mcp_tools.places.schemas import (
    AttractionSearchResult,
    PlacesToolMetadata,
    RestaurantSearchResult,
)
from mcp_tools.weather.schemas import WeatherForecastResult, WeatherToolMetadata

from app.agent.graph import CompiledTripPlannerGraph, compile_trip_planner_graph
from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.schemas import (
    AggregateRunStatus,
    ToolOrchestrationSummary,
)
from app.agent.state import (
    AgentInput,
    AgentState,
    GraphStatus,
    aggregate_run_status_from_state,
    attraction_metadata_from_state,
    attraction_search_from_state,
    budget_result_from_state,
    clarification_from_state,
    critic_result_from_state,
    currency_conversion_from_state,
    currency_metadata_from_state,
    distance_matrix_from_state,
    distance_metadata_from_state,
    flight_metadata_from_state,
    flight_search_from_state,
    hotel_metadata_from_state,
    hotel_search_from_state,
    itinerary_build_result_from_state,
    orchestration_summary_from_state,
    restaurant_metadata_from_state,
    restaurant_search_from_state,
    trip_request_from_state,
    validation_from_state,
    weather_forecast_from_state,
    weather_metadata_from_state,
)
from app.budget.schemas import BudgetResult
from app.domain.trip_request import ClarificationRequest, TripRequest, ValidationResult
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.critic.schemas import CriticResult
from app.itinerary.schemas import ItineraryBuildResult
from app.llm.base import LLMAdapter
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.distance import DistanceTool
from app.tools.flights import FlightTool
from app.tools.hotels import HotelTool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool


@dataclass(frozen=True, slots=True)
class TripPlannerRunResult:
    """Normalized graph execution result for API and test consumers."""

    thread_id: str
    status: GraphStatus
    trip_request: TripRequest | None
    validation: ValidationResult | None
    clarification: ClarificationRequest | None
    weather_forecast: WeatherForecastResult | None
    weather_tool_metadata: WeatherToolMetadata | None
    flight_search: FlightSearchResult | None
    flight_tool_metadata: FlightToolMetadata | None
    hotel_search: HotelSearchResult | None
    hotel_tool_metadata: HotelToolMetadata | None
    distance_matrix: DistanceMatrixResult | None
    distance_tool_metadata: DistanceToolMetadata | None
    restaurant_search: RestaurantSearchResult | None
    restaurant_tool_metadata: PlacesToolMetadata | None
    attraction_search: AttractionSearchResult | None
    attraction_tool_metadata: PlacesToolMetadata | None
    currency_conversion: CurrencyConversionResult | None
    currency_tool_metadata: CurrencyToolMetadata | None
    budget_result: BudgetResult | None
    itinerary_build_result: ItineraryBuildResult | None
    critic_result: CriticResult | None
    planning_failed: bool
    aggregate_run_status: AggregateRunStatus | None
    tool_orchestration_summary: ToolOrchestrationSummary | None
    state: AgentState


class TripPlannerAgentService:
    """Invoke and resume the trip planner LangGraph without exposing node internals."""

    def __init__(
        self,
        graph: CompiledTripPlannerGraph | None = None,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        llm_adapter: LLMAdapter | None = None,
        weather_tool: WeatherTool | None = None,
        flight_tool: FlightTool | None = None,
        airport_resolver: AirportCodeResolver | None = None,
        hotel_tool: HotelTool | None = None,
        city_resolver: CityCodeResolver | None = None,
        distance_tool: DistanceTool | None = None,
        location_resolver: LocationResolver | None = None,
        restaurant_tool: RestaurantTool | None = None,
        attraction_tool: AttractionTool | None = None,
        currency_tool: CurrencyTool | None = None,
        tool_concurrency_limiter: ToolConcurrencyLimiter | None = None,
        itinerary_composer: ItineraryComposer | None = None,
    ) -> None:
        self._checkpointer = checkpointer or InMemorySaver()
        resolved_composer = itinerary_composer or FakeItineraryComposer()
        self._graph = graph or compile_trip_planner_graph(
            checkpointer=self._checkpointer,
            llm_adapter=llm_adapter,
            weather_tool=weather_tool,
            flight_tool=flight_tool,
            airport_resolver=airport_resolver,
            hotel_tool=hotel_tool,
            city_resolver=city_resolver,
            distance_tool=distance_tool,
            location_resolver=location_resolver,
            restaurant_tool=restaurant_tool,
            attraction_tool=attraction_tool,
            currency_tool=currency_tool,
            tool_concurrency_limiter=tool_concurrency_limiter,
            itinerary_composer=resolved_composer,
        )

    def start(
        self,
        user_request: str,
        *,
        thread_id: str | None = None,
    ) -> TripPlannerRunResult:
        """Run the graph for a new planning request."""
        resolved_thread_id = thread_id or str(uuid4())
        graph_input: AgentInput = {"user_request": user_request}
        config: RunnableConfig = {"configurable": {"thread_id": resolved_thread_id}}
        state = self._invoke(graph_input, config)
        return self._to_result(resolved_thread_id, state)

    def resume(
        self,
        thread_id: str,
        user_clarification: str,
    ) -> TripPlannerRunResult:
        """Resume a paused graph thread with additional user clarification."""
        graph_input: AgentInput = {"user_clarification": user_clarification}
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        state = self._invoke(graph_input, config)
        return self._to_result(thread_id, state)

    def get_state(self, thread_id: str) -> TripPlannerRunResult | None:
        """Read the latest checkpointed graph state for a thread."""
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        snapshot = self._graph.get_state(config)
        if snapshot.values is None:
            return None
        state = cast(AgentState, dict(snapshot.values))
        return self._to_result(thread_id, state)

    def _invoke(self, graph_input: AgentInput, config: RunnableConfig) -> AgentState:
        result = self._graph.invoke(graph_input, config=config)
        return cast(AgentState, dict(result))

    def _to_result(self, thread_id: str, state: AgentState) -> TripPlannerRunResult:
        status_value = state.get("status", GraphStatus.EXTRACTING.value)
        summary = orchestration_summary_from_state(state)
        if summary is not None:
            summary = summary.model_copy(update={"run_id": thread_id})
        return TripPlannerRunResult(
            thread_id=thread_id,
            status=GraphStatus(status_value),
            trip_request=trip_request_from_state(state),
            validation=validation_from_state(state),
            clarification=clarification_from_state(state),
            weather_forecast=weather_forecast_from_state(state),
            weather_tool_metadata=weather_metadata_from_state(state),
            flight_search=flight_search_from_state(state),
            flight_tool_metadata=flight_metadata_from_state(state),
            hotel_search=hotel_search_from_state(state),
            hotel_tool_metadata=hotel_metadata_from_state(state),
            distance_matrix=distance_matrix_from_state(state),
            distance_tool_metadata=distance_metadata_from_state(state),
            restaurant_search=restaurant_search_from_state(state),
            restaurant_tool_metadata=restaurant_metadata_from_state(state),
            attraction_search=attraction_search_from_state(state),
            attraction_tool_metadata=attraction_metadata_from_state(state),
            currency_conversion=currency_conversion_from_state(state),
            currency_tool_metadata=currency_metadata_from_state(state),
            budget_result=budget_result_from_state(state),
            itinerary_build_result=itinerary_build_result_from_state(state),
            critic_result=critic_result_from_state(state),
            planning_failed=bool(state.get("planning_failed")),
            aggregate_run_status=aggregate_run_status_from_state(state),
            tool_orchestration_summary=summary,
            state=state,
        )
