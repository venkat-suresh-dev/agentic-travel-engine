"""Tests for reference landmark fusion."""

from __future__ import annotations

from datetime import UTC, datetime

from app.budget.schemas import PriceDataKind
from app.itinerary.catalog import GroundedAttraction, GroundedCatalog
from app.itinerary.reference.fusion import fuse_reference_landmarks
from mcp_tools.places.reference.schemas import (
    LandmarkSearchResult,
    ReferenceLandmark,
    ReferenceLandmarkStatus,
    SignificanceTier,
)

from tests.itinerary.fixtures import example_itinerary_context


class StubWikipediaProvider:
    def search_landmarks(self, request: object) -> LandmarkSearchResult:
        return LandmarkSearchResult(
            source="wikipedia",
            retrieved_at=datetime.now(UTC),
            data_status=ReferenceLandmarkStatus.LIVE,
            landmarks=[
                ReferenceLandmark(
                    place_id="wikipedia:18996255",
                    name="Burj Khalifa",
                    latitude=25.1972,
                    longitude=55.2744,
                    source="wikipedia",
                    reference_page_id=18996255,
                    significance_tier=SignificanceTier.LANDMARK,
                    distance_meters=1200,
                ),
                ReferenceLandmark(
                    place_id="wikipedia:99999",
                    name="Dubai Frame",
                    latitude=25.2356,
                    longitude=55.3003,
                    source="wikipedia",
                    reference_page_id=99999,
                    significance_tier=SignificanceTier.LANDMARK,
                    distance_meters=4000,
                ),
            ],
        )


def test_fusion_enriches_matching_geoapify_poi() -> None:
    context = example_itinerary_context()
    catalog = GroundedCatalog()
    catalog.attractions["geo:burj"] = GroundedAttraction(
        place_id="geo:burj",
        name="Burj Khalifa",
        latitude=25.1973,
        longitude=55.2745,
        primary_type="tourist_attraction",
        source="geoapify",
        data_status=PriceDataKind.LIVE,
        is_indoor=False,
        rating=4.7,
    )
    stats = fuse_reference_landmarks(
        catalog,
        context,
        provider=StubWikipediaProvider(),
    )
    assert stats.matched_to_geoapify == 1
    assert stats.reference_only_added == 1
    enriched = catalog.attractions["geo:burj"]
    assert enriched.significance_tier == SignificanceTier.LANDMARK
    assert enriched.reference_page_id == 18996255
    assert catalog.attractions["wikipedia:99999"].data_status == PriceDataKind.REFERENCE


def test_fusion_adds_reference_only_landmark() -> None:
    context = example_itinerary_context()
    catalog = GroundedCatalog()
    stats = fuse_reference_landmarks(
        catalog,
        context,
        provider=StubWikipediaProvider(),
    )
    assert stats.reference_only_added == 2
    frame = catalog.attractions["wikipedia:99999"]
    assert frame.source == "wikipedia"
    assert frame.data_status == PriceDataKind.REFERENCE
    assert frame.rating is None
