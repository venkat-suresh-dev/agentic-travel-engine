"""Modification diff currency consistency."""

from __future__ import annotations

from decimal import Decimal

from app.itinerary.schemas import Itinerary
from app.modification.diff import change_facts

from tests.itinerary.fixtures import example_valid_itinerary


def test_change_facts_budget_delta_uses_trip_currency() -> None:
    previous = example_valid_itinerary(duration_days=2)
    current = Itinerary.model_validate(
        {
            **previous.model_dump(mode="json"),
            "budget_total_cost": str(
                Decimal(previous.budget_total_cost) - Decimal("5000")
            ),
            "budget_remaining": str(
                Decimal(previous.budget_remaining) + Decimal("5000")
            ),
        }
    )
    facts = change_facts(previous, current, affected_days=[1])
    budget_fact = next(fact for fact in facts if fact.startswith("Budget"))
    assert previous.budget_currency in budget_fact
    assert "5000" in budget_fact
