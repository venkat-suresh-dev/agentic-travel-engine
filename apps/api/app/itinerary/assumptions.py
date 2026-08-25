"""Configurable deterministic scheduling assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SchedulingAssumptions:
    """Documented defaults for durations, buffers, and travel estimates."""

    day_start_time: time = time(9, 0)
    museum_duration_minutes: int = 90
    meal_duration_minutes: int = 60
    short_attraction_duration_minutes: int = 75
    default_attraction_duration_minutes: int = 90
    travel_buffer_minutes: int = 10
    urban_driving_speed_kmh: Decimal = Decimal("35")
    walking_speed_kmh: Decimal = Decimal("5")
    rainy_day_precipitation_threshold: int = 50
    indoor_attraction_types: frozenset[str] = frozenset(
        {"museum", "art_gallery", "shopping_mall"}
    )
    estimated_meal_cost: Decimal = Decimal("1200")
    estimated_attraction_cost: Decimal = Decimal("800")
