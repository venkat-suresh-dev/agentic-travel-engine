"""Selective provider refresh fan-out for modifications."""

from __future__ import annotations

from langgraph.types import Send

from app.agent.state import AgentState
from app.modification.schemas import RefreshPlan

TOOL_NODE_BY_REFRESH_FIELD: dict[str, str] = {
    "refresh_weather": "fetch_weather",
    "refresh_flights": "search_flights",
    "refresh_hotels": "search_hotels",
    "refresh_distance": "get_distance_matrix",
    "refresh_places": "search_restaurants",
    "refresh_rag": "retrieve_context",
}


def fan_out_modification_tools(state: AgentState) -> list[Send]:
    """Return Send packets only for providers invalidated by a modification."""
    from app.modification.schemas import RefreshPlan as RefreshPlanModel

    raw = state.get("refresh_plan")
    if raw is None:
        return []
    plan = RefreshPlanModel.model_validate(raw)
    sends: list[Send] = []
    if plan.refresh_weather:
        sends.append(Send("fetch_weather", state))
    if plan.refresh_flights:
        sends.append(Send("search_flights", state))
    if plan.refresh_hotels:
        sends.append(Send("search_hotels", state))
    if plan.refresh_distance:
        sends.append(Send("get_distance_matrix", state))
    if plan.refresh_places:
        sends.append(Send("search_restaurants", state))
        sends.append(Send("search_attractions", state))
    if plan.refresh_rag:
        sends.append(Send("retrieve_context", state))
    return sends


def modification_tool_node_names(plan: RefreshPlan) -> list[str]:
    """Return node names that will be invoked for a refresh plan."""
    names: list[str] = []
    if plan.refresh_weather:
        names.append("fetch_weather")
    if plan.refresh_flights:
        names.append("search_flights")
    if plan.refresh_hotels:
        names.append("search_hotels")
    if plan.refresh_distance:
        names.append("get_distance_matrix")
    if plan.refresh_places:
        names.extend(["search_restaurants", "search_attractions"])
    if plan.refresh_rag:
        names.append("retrieve_context")
    if plan.refresh_currency:
        names.append("convert_currency")
    return names
