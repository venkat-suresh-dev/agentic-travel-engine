"""Configurable deterministic scheduling assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal

_MEAL_COST_BY_PRICE_LEVEL: dict[str, Decimal] = {
    "inexpensive": Decimal("800"),
    "moderate": Decimal("1200"),
    "expensive": Decimal("1800"),
    "very_expensive": Decimal("2500"),
}


@dataclass(frozen=True, slots=True)
class SchedulingAssumptions:
    """Documented defaults for durations, buffers, and travel estimates."""

    day_start_time: time = time(9, 0)
    relaxed_day_start_time: time = time(10, 0)
    museum_duration_minutes: int = 90
    meal_duration_minutes: int = 60
    short_attraction_duration_minutes: int = 75
    default_attraction_duration_minutes: int = 90
    travel_buffer_minutes: int = 10
    relaxed_travel_buffer_minutes: int = 20
    free_time_duration_minutes: int = 45
    urban_driving_speed_kmh: Decimal = Decimal("35")
    walking_speed_kmh: Decimal = Decimal("5")
    rainy_day_precipitation_threshold: int = 50
    indoor_attraction_types: frozenset[str] = frozenset(
        {"museum", "art_gallery", "shopping_mall"}
    )
    estimated_meal_cost: Decimal = Decimal("1200")
    estimated_attraction_cost: Decimal = Decimal("800")

    def meal_cost_for_price_level(self, price_level: str | None) -> Decimal:
        if price_level is None:
            return self.estimated_meal_cost
        return _MEAL_COST_BY_PRICE_LEVEL.get(price_level, self.estimated_meal_cost)
