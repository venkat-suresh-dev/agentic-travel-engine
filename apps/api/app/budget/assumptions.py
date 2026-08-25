"""Default deterministic planning assumptions for estimated categories."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BudgetAssumptions:
    """Explicit estimate defaults; never used to replace unavailable provider facts."""

    food_per_traveler_per_day: Decimal = Decimal("1200")
    activity_per_traveler_per_day: Decimal = Decimal("900")
    transport_per_trip: Decimal = Decimal("5000")
    other_per_trip: Decimal = Decimal("3000")

    def food_total(self, *, travelers: int, duration_days: int) -> Decimal:
        return (
            self.food_per_traveler_per_day * Decimal(travelers) * Decimal(duration_days)
        )

    def activity_total(self, *, travelers: int, duration_days: int) -> Decimal:
        return (
            self.activity_per_traveler_per_day
            * Decimal(travelers)
            * Decimal(duration_days)
        )
