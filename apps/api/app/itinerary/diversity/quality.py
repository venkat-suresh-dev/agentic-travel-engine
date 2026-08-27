"""Trip diversity metrics and quality validation."""

from __future__ import annotations

from dataclasses import dataclass

from app.itinerary.catalog import GroundedCatalog
from app.itinerary.diversity.geography import cluster_attractions, region_for_attraction
from app.itinerary.schemas import Itinerary, ItinerarySelectionCandidate


@dataclass(frozen=True, slots=True)
class TripDiversityMetrics:
    unique_attractions: int
    unique_restaurants: int
    unique_regions: int
    unique_categories: int
    repeated_source_ids: int
    days_with_meaningful_activities: int
    sparse_days: list[int]
    repeated_attractions: list[str]
    repeated_restaurants: list[str]


def assess_trip_diversity(
    candidate: ItinerarySelectionCandidate | None,
    itinerary: Itinerary | None,
    catalog: GroundedCatalog,
) -> TripDiversityMetrics:
    """Compute deterministic diversity metrics for a trip."""
    attraction_ids: list[str] = []
    restaurant_ids: list[str] = []
    source_ids: list[str] = []
    categories: set[str] = set()
    days_with_activities = 0
    sparse_days: list[int] = []

    if candidate is not None:
        for candidate_day in candidate.days:
            attraction_ids.extend(candidate_day.attraction_source_ids)
            restaurant_ids.append(candidate_day.restaurant_source_id)
            if len(candidate_day.attraction_source_ids) >= 2:
                days_with_activities += 1
            elif len(candidate_day.attraction_source_ids) == 0:
                sparse_days.append(candidate_day.day_number)
            for attraction_id in candidate_day.attraction_source_ids:
                attraction = catalog.attractions.get(attraction_id)
                if attraction is not None:
                    source_ids.append(attraction.place_id)
                    if attraction.primary_type:
                        categories.add(attraction.primary_type)
            restaurant = catalog.restaurants.get(candidate_day.restaurant_source_id)
            if restaurant is not None:
                source_ids.append(restaurant.place_id)
    elif itinerary is not None:
        for itinerary_day in itinerary.days:
            day_attractions = [
                item.source_id
                for item in itinerary_day.items
                if item.category.value == "attraction" and item.source_id
            ]
            attraction_ids.extend(day_attractions)
            if len(day_attractions) >= 2:
                days_with_activities += 1
            elif len(day_attractions) == 0:
                sparse_days.append(itinerary_day.day_number)
            for item in itinerary_day.items:
                if item.source_id:
                    source_ids.append(item.source_id)
                if item.category.value == "attraction" and item.source_id:
                    attraction = catalog.attractions.get(item.source_id)
                    if attraction is not None and attraction.primary_type:
                        categories.add(attraction.primary_type)
            if itinerary_day.meal is not None and itinerary_day.meal.item.source_id:
                restaurant_ids.append(itinerary_day.meal.item.source_id)

    regions = cluster_attractions(catalog, num_regions=5)
    used_regions: set[int] = set()
    for attraction_id in set(attraction_ids):
        region_id = region_for_attraction(attraction_id, regions)
        if region_id is not None:
            used_regions.add(region_id)

    repeated_attractions = _repeated_values(attraction_ids)
    repeated_restaurants = _repeated_values(restaurant_ids)
    repeated_sources = len(_repeated_values(source_ids))

    return TripDiversityMetrics(
        unique_attractions=len(set(attraction_ids)),
        unique_restaurants=len(set(restaurant_ids)),
        unique_regions=len(used_regions),
        unique_categories=len(categories),
        repeated_source_ids=repeated_sources,
        days_with_meaningful_activities=days_with_activities,
        sparse_days=sparse_days,
        repeated_attractions=repeated_attractions,
        repeated_restaurants=repeated_restaurants,
    )


def _repeated_values(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return [value for value, count in counts.items() if count > 1]
