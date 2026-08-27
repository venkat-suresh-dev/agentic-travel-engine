"""Tests for deterministic place quality filtering."""

from __future__ import annotations

from app.budget.schemas import PriceDataKind
from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
from app.itinerary.quality.place_quality import (
    disambiguate_title,
    filter_catalog_quality,
    score_attraction,
)


def test_low_signal_attraction_scores_poorly() -> None:
    weak = GroundedAttraction(
        place_id="weak",
        name="7 ton scotch crane",
        latitude=25.0,
        longitude=55.0,
        primary_type=None,
        source="geoapify",
        data_status=PriceDataKind.LIVE,
        is_indoor=False,
    )
    strong = GroundedAttraction(
        place_id="strong",
        name="Dubai Museum",
        latitude=25.26,
        longitude=55.29,
        primary_type="museum",
        source="geoapify",
        data_status=PriceDataKind.LIVE,
        is_indoor=True,
        rating=4.5,
        user_rating_count=1000,
    )
    assert score_attraction(weak) < score_attraction(strong)


def test_filter_catalog_dedupes_duplicate_names() -> None:
    catalog = GroundedCatalog(
        attractions={
            "a": GroundedAttraction(
                place_id="a",
                name="Al Ghubaiba",
                latitude=25.26,
                longitude=55.29,
                primary_type="tourist_attraction",
                source="geoapify",
                data_status=PriceDataKind.LIVE,
                is_indoor=False,
                rating=4.0,
            ),
            "b": GroundedAttraction(
                place_id="b",
                name="Al Ghubaiba",
                latitude=25.27,
                longitude=55.30,
                primary_type="tourist_attraction",
                source="geoapify",
                data_status=PriceDataKind.LIVE,
                is_indoor=False,
            ),
            "c": GroundedAttraction(
                place_id="c",
                name="Al Shindagha Museum",
                latitude=25.26,
                longitude=55.29,
                primary_type="museum",
                source="geoapify",
                data_status=PriceDataKind.LIVE,
                is_indoor=True,
                rating=4.6,
            ),
        }
    )
    filtered, stats = filter_catalog_quality(catalog)
    assert stats.attractions_rejected_duplicate_name >= 1
    assert len(filtered.attractions) == 2


def test_disambiguate_title_adds_locality() -> None:
    title = disambiguate_title(
        "Al Ghubaiba",
        address="Al Fahidi, Dubai, UAE",
        primary_type="tourist_attraction",
        used_titles={"Al Ghubaiba"},
    )
    assert "Al Ghubaiba" in title
    assert title != "Al Ghubaiba"
