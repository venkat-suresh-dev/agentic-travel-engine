"""Tests for SerpApi flight normalization."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from mcp_tools.flights.providers.serpapi_normalize import parse_serpapi_flight_offers
from mcp_tools.flights.schemas import CabinClass, FlightSearchRequest

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_serpapi_flight_offers() -> None:
    payload = json.loads((FIXTURES / "serpapi_flights.json").read_text())
    request = FlightSearchRequest(
        origin="BOM",
        destination="DXB",
        departure_date=date(2026, 9, 1),
        travelers=2,
        cabin_class=CabinClass.ECONOMY,
        currency="INR",
    )
    offers = parse_serpapi_flight_offers(payload, request=request)
    assert len(offers) == 1
    offer = offers[0]
    assert offer.origin == "BOM"
    assert offer.destination == "DXB"
    assert offer.carrier == "Emirates"
    assert offer.price_amount == Decimal("28500")
    assert offer.price_currency == "INR"
    assert offer.stops == 0
