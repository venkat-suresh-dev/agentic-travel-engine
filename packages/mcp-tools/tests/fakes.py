"""Fake weather providers for offline tests."""

from __future__ import annotations

from mcp_tools.weather.geocoding.base import GeocodedLocation
from mcp_tools.weather.schemas import DailyForecast, WeatherForecastRequest


class FakeGeocodingProvider:
    def geocode(self, location: str) -> GeocodedLocation:
        return GeocodedLocation(
            name=location.title(),
            latitude=25.2048,
            longitude=55.2708,
            country="United Arab Emirates",
        )


class FakeWeatherProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        forecasts: list[DailyForecast] | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.forecasts = forecasts

    def fetch_forecast(
        self,
        request: WeatherForecastRequest,
        location: GeocodedLocation,
    ) -> list[DailyForecast]:
        if self.should_fail:
            from mcp_tools.weather.exceptions import WeatherProviderError

            raise WeatherProviderError("simulated provider failure")
        if self.malformed:
            from mcp_tools.weather.exceptions import WeatherMalformedResponseError

            raise WeatherMalformedResponseError("simulated malformed response")
        if self.forecasts is not None:
            return self.forecasts
        return [
            DailyForecast(
                date=request.start_date,
                temperature_max_c=34.0,
                temperature_min_c=24.0,
                precipitation_probability_max=10,
                weather_summary="Clear sky",
                weather_code=0,
            )
        ]


class FailingGeocodingProvider:
    def geocode(self, location: str) -> GeocodedLocation:
        from mcp_tools.weather.exceptions import GeocodingError

        raise GeocodingError(f"location not found: {location}")


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
            from mcp_tools.flights.exceptions import AirportResolutionError

            raise AirportResolutionError(f"location not found: {location}")
        return code


class FakeFlightProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        fixture_payload: object | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.fixture_payload = fixture_payload

    def search_flights(self, request):  # type: ignore[no-untyped-def]
        from datetime import datetime
        from decimal import Decimal

        from mcp_tools.flights.exceptions import (
            FlightMalformedResponseError,
            FlightProviderError,
        )
        from mcp_tools.flights.providers.normalize import parse_amadeus_flight_offers
        from mcp_tools.flights.schemas import (
            FlightItinerary,
            FlightOffer,
            FlightSegment,
        )

        if self.should_fail:
            raise FlightProviderError("simulated provider failure")
        if self.malformed:
            raise FlightMalformedResponseError("simulated malformed response")
        if self.fixture_payload is not None:
            return parse_amadeus_flight_offers(self.fixture_payload, request=request)
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
                price_currency=request.currency,
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
