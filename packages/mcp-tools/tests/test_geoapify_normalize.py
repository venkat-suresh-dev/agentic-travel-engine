"""Tests for Geoapify places normalization."""

from __future__ import annotations

import json
from pathlib import Path

from mcp_tools.places.providers.geoapify_normalize import (
    parse_geoapify_restaurant_places,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_geoapify_restaurant_places() -> None:
    payload = json.loads((FIXTURES / "geoapify_restaurants.json").read_text())
    restaurants = parse_geoapify_restaurant_places(payload)
    assert len(restaurants) == 1
    restaurant = restaurants[0]
    assert restaurant.place_id == "geoapify-rest-1"
    assert restaurant.name == "Arabian Tea House"
    assert restaurant.latitude == 25.2631
    assert restaurant.longitude == 55.2972
