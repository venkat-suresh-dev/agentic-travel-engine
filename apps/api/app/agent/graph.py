"""Trip planner LangGraph definition."""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from mcp_tools.distance.locations.base import LocationResolver
from mcp_tools.flights.airports.base import AirportCodeResolver
from mcp_tools.hotels.locations.base import CityCodeResolver

from app.agent.nodes.aggregate_independent_tools import (
    build_aggregate_independent_tools_node,
)
from app.agent.nodes.apply_modification import build_apply_modification_node
from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.build_itinerary import build_build_itinerary_node
from app.agent.nodes.compute_budget import build_compute_budget_node
from app.agent.nodes.convert_currency import build_convert_currency_node
from app.agent.nodes.critic_validate import build_critic_validate_node
from app.agent.nodes.extract_modification import build_extract_modification_node
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.nodes.fetch_weather import build_fetch_weather_node
from app.agent.nodes.finalize_failure import build_finalize_failure_node
from app.agent.nodes.finalize_modification_failure import (
    build_finalize_modification_failure_node,
)
from app.agent.nodes.finalize_run import build_finalize_run_node
from app.agent.nodes.get_distance_matrix import build_get_distance_matrix_node
from app.agent.nodes.recompute_modification_budget import (
    build_recompute_modification_budget_node,
)
from app.agent.nodes.resolve_modification_scope import (
    build_resolve_modification_scope_node,
)
from app.agent.nodes.retrieve_context import build_retrieve_context_node
from app.agent.nodes.search_attractions import build_search_attractions_node
from app.agent.nodes.search_flights import build_search_flights_node
from app.agent.nodes.search_hotels import build_search_hotels_node
from app.agent.nodes.search_restaurants import build_search_restaurants_node
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.orchestration.concurrency import ToolConcurrencyLimiter
from app.agent.orchestration.fan_out import INDEPENDENT_TOOL_NODE_NAMES
from app.agent.routing import (
    route_after_aggregate,
    route_after_apply_modification,
    route_after_convert_currency,
    route_after_critic,
    route_after_modification_scope,
    route_after_retrieve_context,
    route_after_validation,
    route_entry,
)
from app.agent.state import AgentInput, AgentState
from app.core.config import Settings, settings
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.composer.llm import LLMItineraryComposer
from app.llm.base import LLMAdapter
from app.llm.factory import build_llm_adapter
from app.rag.service import RAGRetriever
from app.tools.attractions import AttractionTool
from app.tools.currency import CurrencyTool
from app.tools.currency_factory import build_currency_tool
from app.tools.distance import DistanceTool
from app.tools.distance_factory import build_distance_tool, build_location_resolver
from app.tools.flights import FlightTool
from app.tools.flights_factory import build_airport_resolver, build_flight_tool
from app.tools.hotels import HotelTool
from app.tools.hotels_factory import build_city_resolver, build_hotel_tool
from app.tools.places_factory import build_attraction_tool, build_restaurant_tool
from app.tools.restaurants import RestaurantTool
from app.tools.weather import WeatherTool

CompiledTripPlannerGraph = CompiledStateGraph[AgentState, None, AgentInput, AgentState]


def build_trip_planner_graph(
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
    rag_retriever: RAGRetriever | None = None,
    itinerary_composer: ItineraryComposer | None = None,
    config: Settings | None = None,
) -> StateGraph[AgentState, None, AgentInput, AgentState]:
    """Construct extract → validate → parallel tool fan-out graph."""
    cfg = config or settings
    adapter = llm_adapter or build_llm_adapter()
    weather = weather_tool or WeatherTool()
    flights = flight_tool or build_flight_tool()
    resolver = airport_resolver or build_airport_resolver()
    hotels = hotel_tool or build_hotel_tool()
    city = city_resolver or build_city_resolver()
    distance = distance_tool or build_distance_tool()
    locations = location_resolver or build_location_resolver()
    restaurants = restaurant_tool or build_restaurant_tool()
    attractions = attraction_tool or build_attraction_tool()
    currency = currency_tool or build_currency_tool()
    limiter = tool_concurrency_limiter or ToolConcurrencyLimiter(
        cfg.agent_tool_concurrency_limit
    )
    composer = itinerary_composer or LLMItineraryComposer(adapter)

    builder: StateGraph[AgentState, None, AgentInput, AgentState] = StateGraph(
        AgentState,
        input_schema=AgentInput,
    )
    builder.add_node(
        "extract_requirements",
        cast(Any, build_extract_requirements_node(adapter)),
    )
    builder.add_node(
        "extract_modification",
        cast(Any, build_extract_modification_node(adapter)),
    )
    builder.add_node(
        "resolve_modification_scope",
        cast(Any, build_resolve_modification_scope_node()),
    )
    builder.add_node(
        "apply_modification",
        cast(Any, build_apply_modification_node()),
    )
    builder.add_node(
        "recompute_modification_budget",
        cast(Any, build_recompute_modification_budget_node()),
    )
    builder.add_node("validate_requirements", validate_requirements)
    builder.add_node(
        "retrieve_context",
        cast(Any, build_retrieve_context_node(rag_retriever)),
    )
    builder.add_node("ask_user", ask_user)
    builder.add_node(
        "fetch_weather",
        cast(Any, build_fetch_weather_node(weather, limiter)),
    )
    builder.add_node(
        "search_flights",
        cast(Any, build_search_flights_node(flights, resolver, limiter)),
    )
    builder.add_node(
        "search_hotels",
        cast(Any, build_search_hotels_node(hotels, city, limiter)),
    )
    builder.add_node(
        "get_distance_matrix",
        cast(Any, build_get_distance_matrix_node(distance, locations, limiter)),
    )
    builder.add_node(
        "search_restaurants",
        cast(Any, build_search_restaurants_node(restaurants, locations, limiter)),
    )
    builder.add_node(
        "search_attractions",
        cast(Any, build_search_attractions_node(attractions, locations, limiter)),
    )
    builder.add_node(
        "aggregate_independent_tools",
        cast(Any, build_aggregate_independent_tools_node()),
    )
    builder.add_node(
        "convert_currency",
        cast(Any, build_convert_currency_node(currency, limiter)),
    )
    builder.add_node("compute_budget", cast(Any, build_compute_budget_node()))
    builder.add_node(
        "build_itinerary",
        cast(Any, build_build_itinerary_node(composer=composer)),
    )
    builder.add_node("critic_validate", cast(Any, build_critic_validate_node()))
    builder.add_node("finalize_run", cast(Any, build_finalize_run_node()))
    builder.add_node("finalize_failure", cast(Any, build_finalize_failure_node()))
    builder.add_node(
        "finalize_modification_failure",
        cast(Any, build_finalize_modification_failure_node()),
    )

    builder.add_conditional_edges(
        START,
        route_entry,
        ["extract_requirements", "extract_modification"],
    )
    builder.add_edge("extract_requirements", "validate_requirements")
    builder.add_edge("extract_modification", "resolve_modification_scope")
    builder.add_conditional_edges(
        "resolve_modification_scope",
        route_after_modification_scope,
        [
            "apply_modification",
            "fetch_weather",
            "search_flights",
            "search_hotels",
            "get_distance_matrix",
            "search_restaurants",
            "search_attractions",
            "retrieve_context",
        ],
    )
    builder.add_conditional_edges(
        "validate_requirements",
        route_after_validation,
        ["retrieve_context", "ask_user"],
    )
    builder.add_conditional_edges(
        "retrieve_context",
        route_after_retrieve_context,
        [*INDEPENDENT_TOOL_NODE_NAMES, "apply_modification"],
    )
    builder.add_edge("ask_user", END)

    for node_name in INDEPENDENT_TOOL_NODE_NAMES:
        builder.add_edge(node_name, "aggregate_independent_tools")

    builder.add_conditional_edges(
        "aggregate_independent_tools",
        route_after_aggregate,
        ["convert_currency", "apply_modification"],
    )
    builder.add_conditional_edges(
        "convert_currency",
        route_after_convert_currency,
        ["compute_budget", "apply_modification"],
    )
    builder.add_conditional_edges(
        "apply_modification",
        route_after_apply_modification,
        [
            "recompute_modification_budget",
            "critic_validate",
            "finalize_modification_failure",
        ],
    )
    builder.add_edge("recompute_modification_budget", "critic_validate")
    builder.add_edge("compute_budget", "build_itinerary")
    builder.add_edge("build_itinerary", "critic_validate")
    builder.add_conditional_edges(
        "critic_validate",
        route_after_critic,
        [
            "finalize_run",
            "build_itinerary",
            "apply_modification",
            "finalize_failure",
            "finalize_modification_failure",
        ],
    )
    builder.add_edge("finalize_run", END)
    builder.add_edge("finalize_failure", END)
    builder.add_edge("finalize_modification_failure", END)
    return builder


def compile_trip_planner_graph(
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
    rag_retriever: RAGRetriever | None = None,
    itinerary_composer: ItineraryComposer | None = None,
    config: Settings | None = None,
) -> CompiledTripPlannerGraph:
    """Compile the trip planner graph with an optional checkpoint backend."""
    saver = checkpointer or InMemorySaver()
    return build_trip_planner_graph(
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
        rag_retriever=rag_retriever,
        itinerary_composer=itinerary_composer,
        config=config,
    ).compile(
        checkpointer=saver,
    )
