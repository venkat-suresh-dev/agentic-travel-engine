"""Destination significance and experience-theme classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mcp_tools.places.reference.schemas import SignificanceTier

from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
from app.itinerary.reference.fusion import is_landmark_tier

HERITAGE_TYPES = frozenset({"historical_landmark", "place_of_worship"})
CULTURE_TYPES = frozenset({"museum", "art_gallery"})
NATURE_TYPES = frozenset({"park", "zoo", "amusement_park"})
SHOPPING_TYPES = frozenset({"shopping_mall"})

MODERN_KEYWORDS = (
    "tower",
    "burj",
    "frame",
    "mall",
    "opera",
    "arena",
    "planet",
    "aquarium",
    "sky",
    "downtown",
    "plaza",
)
WATERFRONT_KEYWORDS = (
    "marina",
    "creek",
    "beach",
    "waterfront",
    "palm",
    "fountain",
    "island",
    "harbour",
    "harbor",
    "water",
)
HERITAGE_KEYWORDS = (
    "souq",
    "souk",
    "bazaar",
    "heritage",
    "fort",
    "mosque",
    "temple",
    "palace",
    "old town",
    "historical",
    "museum",
)


class ExperienceTheme(StrEnum):
    HERITAGE = "heritage"
    MODERN = "modern"
    WATERFRONT = "waterfront"
    CULTURE = "culture"
    LEISURE = "leisure"
    NATURE = "nature"
    SHOPPING = "shopping"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class TripPreferenceProfile:
    heritage_bias: float = 1.0
    modern_bias: float = 1.0
    waterfront_bias: float = 1.0
    culture_bias: float = 1.0
    leisure_bias: float = 1.0
    is_focused: bool = False


def destination_geographic_center(
    catalog: GroundedCatalog,
) -> tuple[float, float] | None:
    """BBox center across all candidates — less biased than POI-cluster centroid."""
    if not catalog.attractions:
        return None
    lats = [item.latitude for item in catalog.attractions.values()]
    lngs = [item.longitude for item in catalog.attractions.values()]
    return (min(lats) + max(lats)) / 2, (min(lngs) + max(lngs)) / 2


def destination_significance(attraction: GroundedAttraction) -> float:
    """Deterministic 0.0–1.0 significance from grounded evidence only."""
    score = attraction.quality_score if attraction.quality_score is not None else 0.5

    if attraction.significance_tier == SignificanceTier.LANDMARK:
        score = max(score, 0.85)
    elif attraction.significance_tier == SignificanceTier.REFERENCE_LANDMARK:
        score = max(score, 0.68)
    if attraction.reference_source:
        score = max(score, 0.62)

    primary = attraction.primary_type or ""
    if primary in HERITAGE_TYPES | CULTURE_TYPES | {"tourist_attraction"}:
        score += 0.08
    if attraction.rating is not None:
        score += min(0.08, attraction.rating / 5.0 * 0.08)
    if attraction.user_rating_count is not None and attraction.user_rating_count >= 100:
        score += 0.05

    return max(0.0, min(1.0, score))


def classify_experience_theme(attraction: GroundedAttraction) -> ExperienceTheme:
    """Map a grounded attraction to a coarse experience theme."""
    primary = attraction.primary_type or ""
    name_lower = attraction.name.lower()

    if primary in SHOPPING_TYPES or any(
        token in name_lower for token in ("mall", "shopping", "market")
    ):
        if any(
            token in name_lower for token in ("souq", "souk", "bazaar", "spice", "gold")
        ):
            return ExperienceTheme.HERITAGE
        return ExperienceTheme.SHOPPING

    if primary in NATURE_TYPES or any(
        token in name_lower for token in ("park", "garden", "zoo", "beach")
    ):
        return ExperienceTheme.NATURE

    if any(token in name_lower for token in WATERFRONT_KEYWORDS):
        return ExperienceTheme.WATERFRONT

    if any(token in name_lower for token in MODERN_KEYWORDS):
        return ExperienceTheme.MODERN

    if primary in HERITAGE_TYPES or any(
        token in name_lower for token in HERITAGE_KEYWORDS
    ):
        return ExperienceTheme.HERITAGE

    if primary in CULTURE_TYPES:
        return ExperienceTheme.CULTURE

    if primary in {"tourist_attraction", "entertainment"} or is_landmark_tier(
        attraction
    ):
        if destination_significance(attraction) >= 0.75:
            return ExperienceTheme.MODERN
        return ExperienceTheme.LEISURE

    return ExperienceTheme.GENERAL


def build_preference_profile(preferences: list[str]) -> TripPreferenceProfile:
    """Derive theme biases from explicit user preferences."""
    text = " ".join(preferences).lower()
    heritage = 1.0
    modern = 1.0
    waterfront = 1.0
    culture = 1.0
    leisure = 1.0
    focused = False

    if any(
        token in text
        for token in (
            "heritage",
            "local culture",
            "cultural",
            "tradition",
            "history",
            "souk",
            "souq",
        )
    ):
        heritage = 1.65
        culture = max(culture, 1.35)
        focused = True
    if any(token in text for token in ("food", "culinary", "dining", "restaurant")):
        leisure = 1.35
        heritage = max(heritage, 1.25)
        focused = True
    if any(
        token in text
        for token in ("modern", "skyline", "contemporary", "iconic", "landmark")
    ):
        modern = 1.65
        focused = True
    if any(
        token in text
        for token in ("waterfront", "beach", "marina", "creek", "coastal", "water")
    ):
        waterfront = 1.65
        modern = max(modern, 1.2)
        focused = True
    if "more culture" in text:
        culture = 1.55
        heritage = max(heritage, 1.3)
        focused = True
    if "less shopping" in text:
        leisure = max(leisure, 1.1)
        focused = True

    return TripPreferenceProfile(
        heritage_bias=heritage,
        modern_bias=modern,
        waterfront_bias=waterfront,
        culture_bias=culture,
        leisure_bias=leisure,
        is_focused=focused,
    )


def theme_preference_weight(
    theme: ExperienceTheme,
    profile: TripPreferenceProfile,
) -> float:
    weights = {
        ExperienceTheme.HERITAGE: profile.heritage_bias,
        ExperienceTheme.MODERN: profile.modern_bias,
        ExperienceTheme.WATERFRONT: profile.waterfront_bias,
        ExperienceTheme.CULTURE: profile.culture_bias,
        ExperienceTheme.LEISURE: profile.leisure_bias,
        ExperienceTheme.NATURE: profile.leisure_bias,
        ExperienceTheme.SHOPPING: 0.85 if profile.is_focused else 1.0,
        ExperienceTheme.GENERAL: 1.0,
    }
    return weights.get(theme, 1.0)


def count_landmark_pool(catalog: GroundedCatalog) -> int:
    return sum(1 for item in catalog.attractions.values() if is_landmark_tier(item))
