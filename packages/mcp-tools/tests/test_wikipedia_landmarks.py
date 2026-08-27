"""Tests for Wikipedia landmark discovery."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_tools.places.reference.wikipedia import WikipediaLandmarkProvider

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_wikipedia_geosearch_fixture() -> None:
    payload = json.loads((FIXTURES / "wikipedia_geosearch.json").read_text())
    provider = WikipediaLandmarkProvider()
    pages = payload["query"]["geosearch"]
    landmarks: list = []
    for page in pages:
        if (parsed := provider._parse_page(page, destination_name="Dubai")) is not None:  # noqa: SLF001
            landmarks.append(parsed)
    assert len(landmarks) >= 2
    assert all(landmark.place_id.startswith("wikipedia:") for landmark in landmarks)
    assert any("Burj" in landmark.name for landmark in landmarks)


def test_skips_disambiguation_pages() -> None:
    provider = WikipediaLandmarkProvider()
    result = provider._parse_page(  # noqa: SLF001
        {
            "pageid": 1,
            "title": "Dubai (disambiguation)",
            "lat": 25.0,
            "lon": 55.0,
        },
        destination_name="Dubai",
    )
    assert result is None
