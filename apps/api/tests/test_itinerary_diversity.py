"""Tests for trip diversity selection and quality metrics."""

from __future__ import annotations

from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.diversity.quality import assess_trip_diversity
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.validator import validate_candidate

from tests.itinerary.fixtures import example_itinerary_context, fast_assumptions


def test_diverse_composer_avoids_attraction_repeats_when_pool_allows() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    composer = FakeItineraryComposer(assumptions=fast_assumptions())
    candidate = composer.compose(context=context, catalog=catalog)

    validation = validate_candidate(candidate, context=context, catalog=catalog)
    assert validation.is_valid is True

    all_attractions: list[str] = []
    for day in candidate.days:
        all_attractions.extend(day.attraction_source_ids)
    assert len(set(all_attractions)) == len(all_attractions)


def test_diverse_composer_uses_distinct_restaurants() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    candidate = FakeItineraryComposer(assumptions=fast_assumptions()).compose(
        context=context, catalog=catalog
    )

    restaurants = [day.restaurant_source_id for day in candidate.days]
    assert len(set(restaurants)) == len(restaurants)


def test_diversity_metrics_detect_repetition() -> None:
    context = example_itinerary_context(duration_days=3)
    catalog = build_grounded_catalog(context)
    composer = FakeItineraryComposer(assumptions=fast_assumptions())
    candidate = composer.compose(context=context, catalog=catalog)
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
        day_themes=composer.last_themes,
    )

    metrics = assess_trip_diversity(candidate, itinerary, catalog)
    assert metrics.unique_attractions >= 3
    assert metrics.repeated_attractions == []
    assert metrics.repeated_restaurants == []


def test_day_themes_are_materialized() -> None:
    context = example_itinerary_context(duration_days=5)
    catalog = build_grounded_catalog(context)
    composer = FakeItineraryComposer(assumptions=fast_assumptions())
    candidate = composer.compose(context=context, catalog=catalog)
    itinerary = materialize_itinerary(
        candidate,
        context=context,
        catalog=catalog,
        assumptions=fast_assumptions(),
        day_themes=composer.last_themes,
    )

    themed_days = [day for day in itinerary.days if day.day_theme]
    assert len(themed_days) == 5
    titles = [day.day_theme for day in themed_days if day.day_theme]
    assert all(not title.isupper() for title in titles)
    assert len(set(titles)) >= 2


def test_derive_day_theme_prefers_experience_identity() -> None:
    from app.budget.schemas import PriceDataKind
    from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
    from app.itinerary.diversity.themes import derive_day_theme

    catalog = GroundedCatalog()
    catalog.attractions["a"] = GroundedAttraction(
        place_id="a",
        name="Museum",
        latitude=25.2,
        longitude=55.2,
        primary_type="museum",
        source="geoapify",
        data_status=PriceDataKind.LIVE,
        is_indoor=True,
    )
    theme = derive_day_theme(["a"], catalog, region_label="Cultural quarter")
    assert theme.title == "Culture"
    second = derive_day_theme(
        ["a"], catalog, region_label="Cultural quarter", used_titles={"Culture"}
    )
    assert second.title == "Cultural Quarter"
