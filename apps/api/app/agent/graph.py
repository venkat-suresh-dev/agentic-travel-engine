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

from app.agent.nodes.ask_user import ask_user
from app.agent.nodes.convert_currency import build_convert_currency_node
from app.agent.nodes.extract_requirements import build_extract_requirements_node
from app.agent.nodes.fetch_weather import build_fetch_weather_node
from app.agent.nodes.get_distance_matrix import build_get_distance_matrix_node
from app.agent.nodes.search_attractions import build_search_attractions_node
from app.agent.nodes.search_flights import build_search_flights_node
from app.agent.nodes.search_hotels import build_search_hotels_node
from app.agent.nodes.search_restaurants import build_search_restaurants_node
from app.agent.nodes.validate_requirements import validate_requirements
from app.agent.routing import route_after_validation
from app.agent.state import AgentInput, AgentState
from app.llm.base import LLMAdapter
from app.llm.factory import build_llm_adapter
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
) -> StateGraph[AgentState, None, AgentInput, AgentState]:
    """Construct extract → validate → ask_user/weather/flights/hotels/places graph."""
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

    builder: StateGraph[AgentState, None, AgentInput, AgentState] = StateGraph(
        AgentState,
        input_schema=AgentInput,
    )
    builder.add_node(
        "extract_requirements",
        cast(Any, build_extract_requirements_node(adapter)),
    )
    builder.add_node("validate_requirements", validate_requirements)
    builder.add_node("ask_user", ask_user)
    builder.add_node(
        "fetch_weather",
        cast(Any, build_fetch_weather_node(weather)),
    )
    builder.add_node(
        "search_flights",
        cast(Any, build_search_flights_node(flights, resolver)),
    )
    builder.add_node(
        "search_hotels",
        cast(Any, build_search_hotels_node(hotels, city)),
    )
    builder.add_node(
        "get_distance_matrix",
        cast(Any, build_get_distance_matrix_node(distance, locations)),
    )
    builder.add_node(
        "search_restaurants",
        cast(Any, build_search_restaurants_node(restaurants, locations)),
    )
    builder.add_node(
        "search_attractions",
        cast(Any, build_search_attractions_node(attractions, locations)),
    )
    builder.add_node(
        "convert_currency",
        cast(Any, build_convert_currency_node(currency)),
    )

    builder.add_edge(START, "extract_requirements")
    builder.add_edge("extract_requirements", "validate_requirements")
    builder.add_conditional_edges(
        "validate_requirements",
        route_after_validation,
        {
            "fetch_weather": "fetch_weather",
            "ask_user": "ask_user",
        },
    )
    builder.add_edge("ask_user", END)
    builder.add_edge("fetch_weather", "search_flights")
    builder.add_edge("search_flights", "search_hotels")
    builder.add_edge("search_hotels", "get_distance_matrix")
    builder.add_edge("get_distance_matrix", "search_restaurants")
    builder.add_edge("search_restaurants", "search_attractions")
    builder.add_edge("search_attractions", "convert_currency")
    builder.add_edge("convert_currency", END)
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
    ).compile(
        checkpointer=saver,
    )
