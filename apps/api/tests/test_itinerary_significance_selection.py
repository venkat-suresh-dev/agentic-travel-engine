"""Tests for significance-aware itinerary selection."""

from __future__ import annotations

from app.budget.schemas import PriceDataKind
from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
from app.itinerary.diversity.selection import compose_diverse_itinerary
from app.itinerary.diversity.significance import (
    ExperienceTheme,
    build_preference_profile,
    classify_experience_theme,
    destination_significance,
)
from app.itinerary.reference.fusion import is_landmark_tier
from mcp_tools.places.reference.schemas import SignificanceTier

from tests.itinerary.fixtures import example_itinerary_context, fast_assumptions


def _attraction(
    place_id: str,
    name: str,
    lat: float,
    lng: float,
    *,
    primary_type: str = "tourist_attraction",
    tier: SignificanceTier = SignificanceTier.POI,
    quality: float = 0.5,
) -> GroundedAttraction:
    return GroundedAttraction(
        place_id=place_id,
        name=name,
        latitude=lat,
        longitude=lng,
        primary_type=primary_type,
        source="geoapify",
        data_status=PriceDataKind.LIVE,
        is_indoor=False,
        significance_tier=tier,
        quality_score=quality,
    )


def _spread_catalog() -> GroundedCatalog:
    catalog = GroundedCatalog()
    catalog.attractions = {
        "heritage-1": _attraction(
            "heritage-1",
            "Old Souk",
            25.27,
            55.30,
            primary_type="historical_landmark",
            tier=SignificanceTier.LANDMARK,
            quality=0.9,
        ),
        "heritage-2": _attraction(
            "heritage-2",
            "Heritage Museum",
            25.268,
            55.298,
            primary_type="museum",
            tier=SignificanceTier.LANDMARK,
            quality=0.88,
        ),
        "modern-1": _attraction(
            "modern-1",
            "Sky Tower",
            25.197,
            55.274,
            primary_type="tourist_attraction",
            tier=SignificanceTier.LANDMARK,
            quality=0.92,
        ),
        "modern-2": _attraction(
            "modern-2",
            "City Opera",
            25.195,
            55.271,
            primary_type="tourist_attraction",
            tier=SignificanceTier.LANDMARK,
            quality=0.9,
        ),
        "water-1": _attraction(
            "water-1",
            "Marina Walk",
            25.08,
            55.14,
            primary_type="park",
            tier=SignificanceTier.LANDMARK,
            quality=0.86,
        ),
        "local-1": _attraction(
            "local-1",
            "Local Gallery",
            25.22,
            55.28,
            primary_type="art_gallery",
            quality=0.55,
        ),
        "local-2": _attraction(
            "local-2",
            "Neighborhood Park",
            25.225,
            55.285,
            primary_type="park",
            quality=0.5,
        ),
    }
    return catalog


def test_destination_significance_prefers_landmark_tier() -> None:
    poi = _attraction("a", "Small Shop", 25.0, 55.0, quality=0.45)
    landmark = _attraction(
        "b",
        "Grand Tower",
        25.1,
        55.1,
        tier=SignificanceTier.LANDMARK,
        quality=0.9,
    )
    assert destination_significance(landmark) > destination_significance(poi)


def test_classify_experience_theme_detects_modern_and_heritage() -> None:
    heritage = _attraction(
        "h",
        "Spice Souk",
        25.0,
        55.0,
        primary_type="historical_landmark",
        tier=SignificanceTier.LANDMARK,
    )
    modern = _attraction(
        "m",
        "Burj Tower",
        25.1,
        55.1,
        tier=SignificanceTier.LANDMARK,
    )
    assert classify_experience_theme(heritage) == ExperienceTheme.HERITAGE
    assert classify_experience_theme(modern) == ExperienceTheme.MODERN


def test_generic_selection_spreads_themes_across_days() -> None:
    context = example_itinerary_context(duration_days=3)
    context = context.model_copy(
        update={
            "trip_request": context.trip_request.model_copy(update={"preferences": []})
        }
    )
    catalog = _spread_catalog_with_restaurants()
    candidate, _ = compose_diverse_itinerary(
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )
    themes: set[ExperienceTheme] = set()
    landmarks = 0
    for day in candidate.days:
        for attraction_id in day.attraction_source_ids:
            attraction = catalog.attractions[attraction_id]
            themes.add(classify_experience_theme(attraction))
            if is_landmark_tier(attraction):
                landmarks += 1
    assert landmarks >= 2
    assert len(themes) >= 2


def test_heritage_preference_skews_toward_heritage() -> None:
    context = example_itinerary_context(duration_days=2)
    context = context.model_copy(
        update={
            "trip_request": context.trip_request.model_copy(
                update={"preferences": ["heritage", "local culture", "food"]}
            )
        }
    )
    catalog = _spread_catalog_with_restaurants()
    candidate, _ = compose_diverse_itinerary(
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )
    heritage_count = 0
    for day in candidate.days:
        for attraction_id in day.attraction_source_ids:
            if (
                classify_experience_theme(catalog.attractions[attraction_id])
                == ExperienceTheme.HERITAGE
            ):
                heritage_count += 1
    assert heritage_count >= 2


def test_modern_waterfront_preference_skews_away_from_heritage_cluster() -> None:
    context = example_itinerary_context(duration_days=2)
    context = context.model_copy(
        update={
            "trip_request": context.trip_request.model_copy(
                update={
                    "preferences": [
                        "modern attractions",
                        "waterfront experiences",
                    ]
                }
            )
        }
    )
    catalog = _spread_catalog_with_restaurants()
    candidate, _ = compose_diverse_itinerary(
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
    )
    modern_or_water = 0
    for day in candidate.days:
        for attraction_id in day.attraction_source_ids:
            theme = classify_experience_theme(catalog.attractions[attraction_id])
            if theme in {ExperienceTheme.MODERN, ExperienceTheme.WATERFRONT}:
                modern_or_water += 1
    assert modern_or_water >= 2


def test_build_preference_profile_marks_focused_requests() -> None:
    profile = build_preference_profile(["heritage", "local culture", "food"])
    assert profile.is_focused is True
    assert profile.heritage_bias > 1.0


def _spread_catalog_with_restaurants() -> GroundedCatalog:
    from app.itinerary.catalog import GroundedRestaurant

    catalog = _spread_catalog()
    catalog.restaurants = {
        "r1": GroundedRestaurant(
            place_id="r1",
            name="Restaurant One",
            latitude=25.2,
            longitude=55.27,
            source="geoapify",
            data_status=PriceDataKind.LIVE,
        ),
        "r2": GroundedRestaurant(
            place_id="r2",
            name="Restaurant Two",
            latitude=25.21,
            longitude=55.28,
            source="geoapify",
            data_status=PriceDataKind.LIVE,
        ),
        "r3": GroundedRestaurant(
            place_id="r3",
            name="Restaurant Three",
            latitude=25.19,
            longitude=55.26,
            source="geoapify",
            data_status=PriceDataKind.LIVE,
        ),
    }
    return catalog
