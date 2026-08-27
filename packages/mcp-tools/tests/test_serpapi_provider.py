"""Tests for SerpApi flight provider request mapping."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from mcp_tools.flights.providers.serpapi import SerpApiFlightProvider
from mcp_tools.flights.schemas import CabinClass, FlightSearchRequest

FIXTURES = Path(__file__).parent / "fixtures"
_DISALLOWED_TRAVEL_CLASS_VALUES = frozenset(
    {"economy", "premium_economy", "business", "first"}
)


@pytest.mark.parametrize(
    ("cabin_class", "expected_travel_class"),
    [
        (CabinClass.ECONOMY, "1"),
        (CabinClass.PREMIUM_ECONOMY, "2"),
        (CabinClass.BUSINESS, "3"),
        (CabinClass.FIRST, "4"),
    ],
)
def test_serpapi_maps_cabin_class_to_numeric_travel_class(
    cabin_class: CabinClass,
    expected_travel_class: str,
) -> None:
    captured_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_params.update(request.url.params.multi_items())
        payload = json.loads((FIXTURES / "serpapi_flights.json").read_text())
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SerpApiFlightProvider(api_key="test-key", client=client)
    request = FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 9, 1),
        return_date=date(2026, 9, 6),
        travelers=2,
        cabin_class=cabin_class,
        currency="INR",
    )

    offers = provider.search_flights(request)

    assert len(offers) == 1
    assert captured_params["travel_class"] == expected_travel_class
    assert captured_params["travel_class"] not in _DISALLOWED_TRAVEL_CLASS_VALUES
    assert captured_params["type"] == "1"
    assert captured_params["departure_id"] == "BOM"
    assert captured_params["arrival_id"] == "DXB"
