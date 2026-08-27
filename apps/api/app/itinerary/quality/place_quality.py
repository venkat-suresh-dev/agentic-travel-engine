"""Deterministic place quality scoring and filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mcp_tools.places.reference.schemas import SignificanceTier

from app.itinerary.catalog import (
    GroundedAttraction,
    GroundedCatalog,
    GroundedRestaurant,
)

TOURISM_TYPES = frozenset(
    {
        "museum",
        "art_gallery",
        "park",
        "historical_landmark",
        "place_of_worship",
        "tourist_attraction",
        "zoo",
        "amusement_park",
    }
)

LOW_SIGNAL_NAME_PATTERNS = (
    re.compile(r"\b(ltd|pvt|llc|inc|trading|general\s+trading)\b", re.I),
    re.compile(r"\b(suparmarke|supermarke|supermarket|grocery)\b", re.I),
    re.compile(r"^\d+\s*ton\b", re.I),
    re.compile(r"\b(scotch crane)\b", re.I),
)

BUSINESS_WITHOUT_TOURISM = re.compile(
    r"\b(office|warehouse|factory|wholesale|dealer|supplier)\b",
    re.I,
)


@dataclass
class QualityFilterStats:
    attractions_retrieved: int = 0
    attractions_rejected_low_quality: int = 0
    attractions_rejected_duplicate_name: int = 0
    attractions_kept: int = 0
    restaurants_retrieved: int = 0
    restaurants_rejected_low_quality: int = 0
    restaurants_kept: int = 0
    landmark_tier_candidates: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)

    def record(self, reason: str) -> None:
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1


def filter_catalog_quality(
    catalog: GroundedCatalog,
) -> tuple[GroundedCatalog, QualityFilterStats]:
    """Filter low-signal places from a grounded catalog before composition."""
    stats = QualityFilterStats(
        attractions_retrieved=len(catalog.attractions),
        restaurants_retrieved=len(catalog.restaurants),
        landmark_tier_candidates=sum(
            1
            for item in catalog.attractions.values()
            if item.significance_tier
            in {SignificanceTier.LANDMARK, SignificanceTier.REFERENCE_LANDMARK}
        ),
    )
    filtered = GroundedCatalog(
        indoor_attraction_types=catalog.indoor_attraction_types,
    )
    filtered.flights = dict(catalog.flights)
    filtered.hotels = dict(catalog.hotels)
    filtered.weather_by_day = dict(catalog.weather_by_day)

    seen_attraction_names: set[str] = set()
    ranked_attractions = sorted(
        catalog.attractions.values(),
        key=lambda item: score_attraction(item),
        reverse=True,
    )
    for attraction in ranked_attractions:
        normalized = _normalize_name(attraction.name)
        quality = score_attraction(attraction)
        min_quality = 0.35 if _is_reference_landmark(attraction) else 0.45
        if quality < min_quality:
            stats.attractions_rejected_low_quality += 1
            stats.record("low_attraction_quality")
            continue
        if normalized in seen_attraction_names:
            stats.attractions_rejected_duplicate_name += 1
            stats.record("duplicate_attraction_name")
            continue
        seen_attraction_names.add(normalized)
        filtered.attractions[attraction.place_id] = attraction
        stats.attractions_kept += 1

    ranked_restaurants = sorted(
        catalog.restaurants.values(),
        key=lambda item: score_restaurant(item),
        reverse=True,
    )
    seen_restaurant_names: set[str] = set()
    for restaurant in ranked_restaurants:
        normalized = _normalize_name(restaurant.name)
        quality = score_restaurant(restaurant)
        if quality < 0.25:
            stats.restaurants_rejected_low_quality += 1
            stats.record("low_restaurant_quality")
            continue
        if normalized in seen_restaurant_names:
            stats.record("duplicate_restaurant_name")
            continue
        seen_restaurant_names.add(normalized)
        filtered.restaurants[restaurant.place_id] = restaurant
        stats.restaurants_kept += 1

    return filtered, stats


def score_attraction(attraction: GroundedAttraction) -> float:
    """Score attraction tourism relevance from 0.0 to 1.0."""
    if attraction.quality_score is not None:
        score = attraction.quality_score
    else:
        score = 0.5
    name = attraction.name.strip()
    if len(name) < 3:
        return 0.0

    if attraction.significance_tier in {
        SignificanceTier.LANDMARK,
        SignificanceTier.REFERENCE_LANDMARK,
    }:
        score += 0.25

    primary = attraction.primary_type or ""
    if primary in TOURISM_TYPES:
        score += 0.25
    elif primary and "tourism" in primary.lower():
        score += 0.15

    if attraction.rating is not None:
        score += min(0.15, attraction.rating / 5.0 * 0.15)
    if attraction.user_rating_count is not None and attraction.user_rating_count >= 50:
        score += 0.1

    name_lower = name.lower()
    if any(pattern.search(name) for pattern in LOW_SIGNAL_NAME_PATTERNS):
        score -= 0.35
    if re.search(r"\bgeat\b", name_lower):
        score -= 0.4
    if re.search(r"\bdesign\b", name_lower) and primary not in TOURISM_TYPES:
        score -= 0.25
    if BUSINESS_WITHOUT_TOURISM.search(name):
        score -= 0.4

    tourism_keywords = (
        "museum",
        "park",
        "mosque",
        "temple",
        "souq",
        "souk",
        "bazaar",
        "beach",
        "tower",
        "fort",
        "palace",
        "garden",
        "marina",
        "heritage",
        "gallery",
        "theatre",
        "theater",
        "aquarium",
        "frame",
        "creek",
        "walk",
        "view",
    )
    if any(keyword in name_lower for keyword in tourism_keywords):
        score += 0.2

    if name.islower() and " " not in name and len(name) < 12:
        score -= 0.15

    return max(0.0, min(1.0, score))


def score_restaurant(restaurant: GroundedRestaurant) -> float:
    """Score restaurant relevance from 0.0 to 1.0."""
    score = 0.55
    name = restaurant.name.strip()
    if len(name) < 2:
        return 0.0
    if restaurant.rating is not None:
        score += min(0.2, restaurant.rating / 5.0 * 0.2)
    if re.search(r"\b(restaurant|cafe|grill|kitchen|bistro|diner)\b", name, re.I):
        score += 0.1
    return max(0.0, min(1.0, score))


def disambiguate_title(
    name: str,
    *,
    address: str | None,
    primary_type: str | None,
    used_titles: set[str],
) -> str:
    """Add locality/category context when display names collide."""
    normalized = _normalize_name(name)
    if not any(_normalize_name(title) == normalized for title in used_titles):
        return name
    parts: list[str] = []
    if address:
        locality = _locality_from_address(address)
        if locality:
            parts.append(locality)
    if primary_type:
        label = primary_type.replace("_", " ").replace(".", " ")
        if label and label.lower() not in name.lower():
            parts.append(label.title())
    if not parts:
        return name
    suffix = " · ".join(parts[:2])
    candidate = f"{name} · {suffix}"
    return candidate if candidate not in used_titles else f"{name} ({suffix})"


def _locality_from_address(address: str) -> str | None:
    segments = [segment.strip() for segment in address.split(",") if segment.strip()]
    if len(segments) >= 2:
        return segments[-2]
    if segments:
        return segments[0]
    return None


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _is_reference_landmark(attraction: GroundedAttraction) -> bool:
    from app.budget.schemas import PriceDataKind

    return (
        attraction.data_status == PriceDataKind.REFERENCE
        or attraction.significance_tier
        in {SignificanceTier.LANDMARK, SignificanceTier.REFERENCE_LANDMARK}
    )
