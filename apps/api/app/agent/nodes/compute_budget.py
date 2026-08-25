"""Compute deterministic trip budget from provider facts and assumptions."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.state import (
    AgentState,
    currency_conversion_from_state,
    flight_search_from_state,
    hotel_search_from_state,
    trip_request_from_state,
)
from app.budget.assumptions import BudgetAssumptions
from app.budget.builder import build_budget_inputs
from app.budget.engine import BudgetEngine
from app.budget.exceptions import BudgetValidationError


def build_compute_budget_node(
    *,
    engine: BudgetEngine | None = None,
    assumptions: BudgetAssumptions | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    """Create a deterministic budget node for the complete-request path."""
    budget_engine = engine or BudgetEngine()
    planning_assumptions = assumptions or BudgetAssumptions()

    def compute_budget(state: AgentState) -> dict[str, object]:
        trip_request = trip_request_from_state(state)
        if trip_request is None:
            return {"budget_result": None}

        try:
            inputs = build_budget_inputs(
                trip_request,
                flight_search=flight_search_from_state(state),
                hotel_search=hotel_search_from_state(state),
                currency_conversion=currency_conversion_from_state(state),
                assumptions=planning_assumptions,
            )
            result = budget_engine.calculate(inputs)
            return {"budget_result": result.model_dump(mode="json")}
        except BudgetValidationError:
            return {"budget_result": None}

    return compute_budget
