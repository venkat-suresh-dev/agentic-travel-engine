"""Fake flight providers for API integration tests."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from mcp_tools.flights.exceptions import (
    AirportResolutionError,
    FlightMalformedResponseError,
    FlightProviderError,
)
from mcp_tools.flights.schemas import (
    FlightItinerary,
    FlightOffer,
    FlightSearchRequest,
    FlightSegment,
)


class FakeAirportCodeResolver:
    _MAPPINGS = {
        "mumbai": "BOM",
        "dubai": "DXB",
        "bom": "BOM",
        "dxb": "DXB",
    }

    def resolve(self, location: str) -> str:
        normalized = location.strip().lower()
        if len(normalized) == 3 and normalized.isalpha():
            return normalized.upper()
        code = self._MAPPINGS.get(normalized)
        if code is None:
            raise AirportResolutionError(f"location not found: {location}")
        return code


class FakeFlightProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        price_currency: str | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.price_currency = price_currency

    def search_flights(self, request: FlightSearchRequest) -> list[FlightOffer]:
        if self.should_fail:
            raise FlightProviderError("simulated provider failure")
        if self.malformed:
            raise FlightMalformedResponseError("simulated malformed response")
        return [
            FlightOffer(
                offer_id="fake-1",
                carrier="EK",
                origin=request.origin,
                destination=request.destination,
                departure_at=datetime(2026, 12, 1, 6, 0),
                arrival_at=datetime(2026, 12, 1, 8, 25),
                duration="PT3H25M",
                stops=0,
                cabin_class=request.cabin_class,
                price_amount=Decimal("45000"),
                price_currency=self.price_currency or request.currency,
                itineraries=[
                    FlightItinerary(
                        duration="PT3H25M",
                        stops=0,
                        segments=[
                            FlightSegment(
                                origin=request.origin,
                                destination=request.destination,
                                departure_at=datetime(2026, 12, 1, 6, 0),
                                arrival_at=datetime(2026, 12, 1, 8, 25),
                                duration="PT3H25M",
                                flight_number="EK501",
                                carrier="EK",
                            )
                        ],
                    )
                ],
            )
        ]
