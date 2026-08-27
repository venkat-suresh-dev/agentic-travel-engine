"""Deterministic diverse candidate selection for itinerary composition."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.clustering import select_weather_aware_attractions
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.diversity.geography import (
    GeographicRegion,
    cluster_attractions,
    region_for_attraction,
)
from app.itinerary.diversity.significance import (
    build_preference_profile,
    classify_experience_theme,
    count_landmark_pool,
    destination_geographic_center,
    destination_significance,
    theme_preference_weight,
)
from app.itinerary.diversity.themes import DayTheme, derive_day_theme
from app.itinerary.reference.fusion import is_landmark_tier
from app.itinerary.schemas import CandidateDayPlan, ItinerarySelectionCandidate
from app.modification.selection import (
    CULTURE_TYPES,
    PRICE_LEVEL_RANK,
    SHOPPING_TYPES,
)

INDOOR_TYPES = frozenset({"museum", "art_gallery", "shopping_mall"})


@dataclass
class TripUsageTracker:
    """Track used entities across a trip for anti-repetition and balance."""

    used_attraction_ids: set[str] = field(default_factory=set)
    used_restaurant_ids: set[str] = field(default_factory=set)
    used_source_ids: set[str] = field(default_factory=set)
    used_names: set[str] = field(default_factory=set)
    used_categories: dict[str, int] = field(default_factory=dict)
    used_regions: dict[int, int] = field(default_factory=dict)
    landmark_selected_count: int = 0
    theme_counts: dict[str, int] = field(default_factory=dict)

    def mark_attraction(
        self,
        attraction_id: str,
        catalog: GroundedCatalog,
        region_id: int | None,
    ) -> None:
        self.used_attraction_ids.add(attraction_id)
        attraction = catalog.attractions.get(attraction_id)
        if attraction is not None:
            self.used_source_ids.add(attraction.place_id)
            self.used_names.add(_normalize_name(attraction.name))
            primary = attraction.primary_type or "other"
            self.used_categories[primary] = self.used_categories.get(primary, 0) + 1
            if is_landmark_tier(attraction):
                self.landmark_selected_count += 1
            theme = classify_experience_theme(attraction).value
            self.theme_counts[theme] = self.theme_counts.get(theme, 0) + 1
        if region_id is not None:
            self.used_regions[region_id] = self.used_regions.get(region_id, 0) + 1

    def mark_restaurant(self, restaurant_id: str, catalog: GroundedCatalog) -> None:
        self.used_restaurant_ids.add(restaurant_id)
        restaurant = catalog.restaurants.get(restaurant_id)
        if restaurant is not None:
            self.used_source_ids.add(restaurant.place_id)
            self.used_names.add(_normalize_name(restaurant.name))
            primary = restaurant.primary_type or "restaurant"
            self.used_categories[primary] = self.used_categories.get(primary, 0) + 1


def compose_diverse_itinerary(
    *,
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
    assumptions: SchedulingAssumptions,
    indoor_override_days: set[int] | None = None,
) -> tuple[ItinerarySelectionCandidate, dict[int, DayTheme]]:
    """Compose a diverse multi-day candidate with themes."""
    duration = context.trip_request.duration_days or 1
    destination_center = destination_geographic_center(catalog)
    center_lat = destination_center[0] if destination_center else None
    center_lng = destination_center[1] if destination_center else None
    regions = cluster_attractions(
        catalog,
        num_regions=min(duration, 5),
        center_lat=center_lat,
        center_lng=center_lng,
    )
    preference_profile = build_preference_profile(context.trip_request.preferences)
    landmark_pool = count_landmark_pool(catalog)
    tracker = TripUsageTracker()
    themes: dict[int, DayTheme] = {}
    days: list[CandidateDayPlan] = []

    for day_number in range(1, duration + 1):
        target_region = _target_region_for_day(
            day_number,
            regions,
            tracker,
            catalog=catalog,
            preference_profile=preference_profile,
        )
        max_items = _items_per_day(day_number, duration, len(catalog.attractions))
        force_indoor = (
            indoor_override_days is not None and day_number in indoor_override_days
        )

        selected = select_day_attractions(
            catalog,
            day_number=day_number,
            max_items=max_items,
            tracker=tracker,
            regions=regions,
            target_region_id=target_region,
            assumptions=assumptions,
            force_indoor=force_indoor,
            duration=duration,
            destination_center=destination_center,
            preference_profile=preference_profile,
            landmark_pool_size=landmark_pool,
        )
        restaurant_id = select_day_restaurant(
            catalog,
            day_number=day_number,
            tracker=tracker,
            attraction_ids=selected,
        )
        if restaurant_id is None:
            raise ValueError("at least one grounded restaurant is required")

        region_label = None
        if target_region is not None:
            for region in regions:
                if region.region_id == target_region:
                    region_label = region.label
                    break

        theme = derive_day_theme(
            selected,
            catalog,
            region_label=region_label,
            used_titles={item.title for item in themes.values()},
        )
        themes[day_number] = theme
        for attraction_id in selected:
            tracker.mark_attraction(
                attraction_id,
                catalog,
                region_for_attraction(attraction_id, regions),
            )
        tracker.mark_restaurant(restaurant_id, catalog)

        days.append(
            CandidateDayPlan(
                day_number=day_number,
                attraction_source_ids=selected,
                restaurant_source_id=restaurant_id,
            )
        )

    return ItinerarySelectionCandidate(days=days), themes


def select_day_attractions(
    catalog: GroundedCatalog,
    *,
    day_number: int,
    max_items: int,
    tracker: TripUsageTracker,
    regions: list[GeographicRegion],
    target_region_id: int | None,
    assumptions: SchedulingAssumptions,
    force_indoor: bool = False,
    duration: int = 1,
    destination_center: tuple[float, float] | None = None,
    preference_profile: object | None = None,
    landmark_pool_size: int = 0,
) -> list[str]:
    """Select diverse attractions for one day using greedy balanced scoring."""
    from app.itinerary.diversity.significance import TripPreferenceProfile

    profile = (
        preference_profile
        if isinstance(preference_profile, TripPreferenceProfile)
        else build_preference_profile([])
    )

    candidates = [
        item
        for item in catalog.attraction_ids()
        if item not in tracker.used_attraction_ids
    ]
    if not candidates:
        return []

    if force_indoor:
        indoor = [item for item in candidates if catalog.attractions[item].is_indoor]
        if indoor:
            candidates = indoor

    selected: list[str] = []
    remaining = list(candidates)

    while len(selected) < max_items and remaining:
        ranked = sorted(
            remaining,
            key=lambda item: _attraction_score(
                item,
                catalog,
                tracker=tracker,
                regions=regions,
                target_region_id=target_region_id,
                day_number=day_number,
                duration=duration,
                destination_center=destination_center,
                preference_profile=profile,
                day_selected_ids=selected,
                landmark_pool_size=landmark_pool_size,
            ),
        )

        weather_filtered = select_weather_aware_attractions(
            ranked,
            day_number=day_number,
            catalog=catalog,
            assumptions=assumptions,
            max_items=1,
        )
        pick = weather_filtered[0] if weather_filtered else ranked[0]
        if pick not in remaining:
            break
        selected.append(pick)
        remaining.remove(pick)

    return _dedupe_names(selected, catalog, max_items)


def select_day_restaurant(
    catalog: GroundedCatalog,
    *,
    day_number: int,
    tracker: TripUsageTracker,
    attraction_ids: list[str],
) -> str | None:
    """Select a distinct restaurant aligned with the day's geography."""
    restaurant_ids = catalog.restaurant_ids()
    if not restaurant_ids:
        return None

    unused = [
        item for item in restaurant_ids if item not in tracker.used_restaurant_ids
    ]
    pool = unused or restaurant_ids

    day_lat, day_lng = _day_centroid(attraction_ids, catalog)
    ranked = sorted(
        pool,
        key=lambda item: _restaurant_score(
            item,
            catalog,
            tracker=tracker,
            day_lat=day_lat,
            day_lng=day_lng,
            day_number=day_number,
        ),
    )
    if not ranked:
        return restaurant_ids[(day_number - 1) % len(restaurant_ids)]
    return ranked[0]


def _target_region_for_day(
    day_number: int,
    regions: list[GeographicRegion],
    tracker: TripUsageTracker,
    *,
    catalog: GroundedCatalog,
    preference_profile: object,
) -> int | None:
    from app.itinerary.diversity.significance import TripPreferenceProfile

    profile = (
        preference_profile
        if isinstance(preference_profile, TripPreferenceProfile)
        else build_preference_profile([])
    )
    if not regions:
        return None
    if len(regions) == 1:
        return regions[0].region_id

    best_region_id: int | None = None
    best_score = float("inf")

    for region in regions:
        unused = [
            item
            for item in region.attraction_ids
            if item not in tracker.used_attraction_ids
        ]
        if not unused:
            continue

        significance_total = sum(
            destination_significance(catalog.attractions[item]) for item in unused[:6]
        )
        landmark_unused = sum(
            1 for item in unused if is_landmark_tier(catalog.attractions[item])
        )
        theme_values = [
            classify_experience_theme(catalog.attractions[item]) for item in unused[:6]
        ]
        theme_fit = sum(
            theme_preference_weight(theme, profile) for theme in theme_values
        ) / max(1, len(theme_values))

        used_penalty = tracker.used_regions.get(region.region_id, 0) * 5
        region_score = (
            used_penalty
            - significance_total * 4
            - landmark_unused * 3
            - (theme_fit - 1.0) * 6
        )

        if region_score < best_score:
            best_score = region_score
            best_region_id = region.region_id

    if best_region_id is not None:
        return best_region_id

    least_used = sorted(
        regions,
        key=lambda region: (
            tracker.used_regions.get(region.region_id, 0),
            region.region_id,
        ),
    )
    return least_used[(day_number - 1) % len(least_used)].region_id


def _items_per_day(day_number: int, duration: int, pool_size: int) -> int:
    if pool_size <= duration:
        return 1
    if duration <= 3:
        return min(3, max(2, pool_size // duration))
    if day_number in {1, duration}:
        return 2
    return min(3, max(2, pool_size // duration))


def _attraction_score(
    attraction_id: str,
    catalog: GroundedCatalog,
    *,
    tracker: TripUsageTracker,
    regions: list[GeographicRegion],
    target_region_id: int | None,
    day_number: int,
    duration: int,
    destination_center: tuple[float, float] | None,
    preference_profile: object,
    day_selected_ids: list[str],
    landmark_pool_size: int,
) -> tuple[int, int, int, float]:
    from app.itinerary.diversity.significance import TripPreferenceProfile

    profile = (
        preference_profile
        if isinstance(preference_profile, TripPreferenceProfile)
        else build_preference_profile([])
    )
    attraction = catalog.attractions[attraction_id]
    primary = attraction.primary_type or "other"
    significance = destination_significance(attraction)
    theme = classify_experience_theme(attraction)

    repeat_penalty = 10 if attraction_id in tracker.used_attraction_ids else 0
    source_penalty = 10 if attraction.place_id in tracker.used_source_ids else 0
    name_penalty = 10 if _normalize_name(attraction.name) in tracker.used_names else 0
    category_penalty = tracker.used_categories.get(primary, 0) * 2

    region_bonus = 0
    if target_region_id is not None:
        region_id = region_for_attraction(attraction_id, regions)
        if region_id == target_region_id:
            cohesion = -1 if significance >= 0.72 else -2
            region_bonus = cohesion
        elif region_id is not None:
            region_bonus = tracker.used_regions.get(region_id, 0) * 2

    culture_bonus = 0 if primary in CULTURE_TYPES else 1
    shopping_penalty = 2 if primary in SHOPPING_TYPES else 0

    significance_bonus = -int(significance * 10)

    landmark_bonus = 0
    theme_weight = theme_preference_weight(theme, profile)
    if is_landmark_tier(attraction) and landmark_pool_size > 0:
        soft_target = max(1, min(duration // 2 + 1, landmark_pool_size // 3))
        if not profile.is_focused:
            gap = soft_target - tracker.landmark_selected_count
            if gap > 0:
                landmark_bonus = -min(8, gap * 3)
        elif theme_weight >= 1.15:
            gap = soft_target - tracker.landmark_selected_count
            if gap > 0:
                landmark_bonus = -min(10, int(gap * 3 * theme_weight))
        elif theme_weight < 1.0:
            landmark_bonus = int((1.0 - theme_weight) * 5)

    theme_bonus = 0
    theme_uses = tracker.theme_counts.get(theme.value, 0)
    if profile.is_focused:
        if theme_weight > 1.0:
            theme_bonus = -int((theme_weight - 1.0) * 14)
        elif theme_weight < 1.0:
            theme_bonus = int((1.0 - theme_weight) * 8)
        if theme_uses >= 2 and theme_weight <= 1.0:
            theme_bonus += theme_uses * 2
    elif tracker.theme_counts:
        avg_uses = sum(tracker.theme_counts.values()) / len(tracker.theme_counts)
        if theme_uses < avg_uses:
            theme_bonus = -3
        elif theme_uses > avg_uses + 1:
            theme_bonus = 2

    within_day_theme_penalty = 0
    for selected_id in day_selected_ids:
        if classify_experience_theme(catalog.attractions[selected_id]) == theme:
            within_day_theme_penalty += 3

    travel_penalty = _travel_penalty(
        attraction,
        day_selected_ids=day_selected_ids,
        catalog=catalog,
        destination_center=destination_center,
        significance=significance,
    )

    rating = -(attraction.rating or 0.0)
    day_rotation = (day_number + hash(attraction_id)) % 7

    total_penalty = (
        repeat_penalty
        + source_penalty
        + name_penalty
        + category_penalty
        + region_bonus
        + shopping_penalty
        + significance_bonus
        + landmark_bonus
        + theme_bonus
        + within_day_theme_penalty
        + travel_penalty
    )
    return (
        total_penalty,
        culture_bonus,
        day_rotation,
        rating,
    )


def _travel_penalty(
    attraction: object,
    *,
    day_selected_ids: list[str],
    catalog: GroundedCatalog,
    destination_center: tuple[float, float] | None,
    significance: float,
) -> int:
    from app.itinerary.catalog import GroundedAttraction

    if not isinstance(attraction, GroundedAttraction):
        return 0

    anchor = _day_anchor(day_selected_ids, catalog, destination_center)
    if anchor is None:
        return 0

    anchor_lat, anchor_lng = anchor
    distance = _haversine_km(
        anchor_lat,
        anchor_lng,
        attraction.latitude,
        attraction.longitude,
    )

    if significance >= 0.82:
        if distance <= 18:
            return 0
        return min(4, int((distance - 18) * 0.4))

    if distance <= 8:
        return 0
    if distance <= 14:
        return int((distance - 8) * 0.6)
    return int(6 + (distance - 14) * 1.2)


def _day_anchor(
    day_selected_ids: list[str],
    catalog: GroundedCatalog,
    destination_center: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if day_selected_ids:
        lat, lng = _day_centroid(day_selected_ids, catalog)
        if lat is not None and lng is not None:
            return lat, lng
    return destination_center


def _restaurant_score(
    restaurant_id: str,
    catalog: GroundedCatalog,
    *,
    tracker: TripUsageTracker,
    day_lat: float | None,
    day_lng: float | None,
    day_number: int,
) -> tuple[int, float, int]:
    restaurant = catalog.restaurants[restaurant_id]
    repeat_penalty = 10 if restaurant_id in tracker.used_restaurant_ids else 0
    source_penalty = 10 if restaurant.place_id in tracker.used_source_ids else 0
    name_penalty = 10 if _normalize_name(restaurant.name) in tracker.used_names else 0
    primary = restaurant.primary_type or "restaurant"
    category_penalty = tracker.used_categories.get(primary, 0) * 2

    distance_penalty = 0.0
    if day_lat is not None and day_lng is not None:
        distance_penalty = _haversine_km(
            day_lat,
            day_lng,
            restaurant.latitude,
            restaurant.longitude,
        )

    price_rank = PRICE_LEVEL_RANK.get(restaurant.price_level or "", 1)
    rating = -(restaurant.rating or 0.0)
    day_rotation = (day_number + hash(restaurant_id)) % 7

    return (
        repeat_penalty
        + source_penalty
        + name_penalty
        + category_penalty
        + int(distance_penalty * 2),
        rating + price_rank * 0.1,
        day_rotation,
    )


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _dedupe_names(
    attraction_ids: list[str],
    catalog: GroundedCatalog,
    max_items: int,
) -> list[str]:
    selected: list[str] = []
    seen_names: set[str] = set()
    for attraction_id in attraction_ids:
        attraction = catalog.attractions.get(attraction_id)
        if attraction is None:
            continue
        normalized = _normalize_name(attraction.name)
        if normalized in seen_names:
            continue
        seen_names.add(normalized)
        selected.append(attraction_id)
        if len(selected) >= max_items:
            break
    return selected


def _day_centroid(
    attraction_ids: list[str],
    catalog: GroundedCatalog,
) -> tuple[float | None, float | None]:
    coords = [
        (catalog.attractions[item].latitude, catalog.attractions[item].longitude)
        for item in attraction_ids
        if item in catalog.attractions
    ]
    if not coords:
        return None, None
    return (
        sum(lat for lat, _ in coords) / len(coords),
        sum(lng for _, lng in coords) / len(coords),
    )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math

    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(a))
