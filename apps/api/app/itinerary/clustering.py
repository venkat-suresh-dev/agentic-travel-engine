"""Geographic clustering and weather-aware attraction selection."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
from app.itinerary.travel import TravelTimeEstimator


def order_attractions_by_proximity(
    attraction_ids: list[str],
    catalog: GroundedCatalog,
    estimator: TravelTimeEstimator,
) -> list[str]:
    """Nearest-neighbor ordering to reduce backtracking within a day."""
    if len(attraction_ids) <= 1:
        return attraction_ids

    remaining = list(attraction_ids)
    ordered: list[str] = []
    current = catalog.attractions[remaining.pop(0)]
    ordered.append(current.place_id)

    while remaining:
        next_id = min(
            remaining,
            key=lambda candidate_id: _travel_seconds(
                current,
                catalog.attractions[candidate_id],
                estimator,
            ),
        )
        remaining.remove(next_id)
        current = catalog.attractions[next_id]
        ordered.append(next_id)

    return ordered


def select_weather_aware_attractions(
    attraction_ids: list[str],
    *,
    day_number: int,
    catalog: GroundedCatalog,
    assumptions: SchedulingAssumptions,
    max_items: int = 2,
) -> list[str]:
    """Prefer indoor attractions on rainy days using weather tool facts."""
    if not attraction_ids:
        return []

    forecast = catalog.weather_by_day.get(day_number)
    precip = forecast.precipitation_probability_max if forecast else None
    rainy = (
        precip is not None and precip >= assumptions.rainy_day_precipitation_threshold
    )

    if not rainy:
        return attraction_ids[:max_items]

    indoor = [
        attraction_id
        for attraction_id in attraction_ids
        if catalog.attractions[attraction_id].is_indoor
    ]
    outdoor = [
        attraction_id
        for attraction_id in attraction_ids
        if not catalog.attractions[attraction_id].is_indoor
    ]
    preferred = indoor + outdoor
    return preferred[:max_items]


def _travel_seconds(
    origin: GroundedAttraction,
    destination: GroundedAttraction,
    estimator: TravelTimeEstimator,
) -> int:
    return estimator.estimate(
        origin_lat=origin.latitude,
        origin_lng=origin.longitude,
        destination_lat=destination.latitude,
        destination_lng=destination.longitude,
    ).duration_seconds
