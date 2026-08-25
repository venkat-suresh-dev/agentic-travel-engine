"""Fake weather providers for offline tests."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.distance.schemas import LocationPoint
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


class FakeCityCodeResolver:
    _MAPPINGS = {
        "dubai": "DXB",
        "mumbai": "BOM",
        "paris": "PAR",
        "dxb": "DXB",
        "bom": "BOM",
        "par": "PAR",
    }

    def resolve(self, location: str) -> str:
        normalized = location.strip().lower()
        if len(normalized) == 3 and normalized.isalpha():
            return normalized.upper()
        code = self._MAPPINGS.get(normalized)
        if code is None:
            from mcp_tools.hotels.exceptions import CityResolutionError

            raise CityResolutionError(f"location not found: {location}")
        return code


class FakeHotelProvider:
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

    def search_hotels(self, request):  # type: ignore[no-untyped-def]
        from decimal import Decimal

        from mcp_tools.hotels.exceptions import (
            HotelMalformedResponseError,
            HotelProviderError,
        )
        from mcp_tools.hotels.providers.normalize import parse_amadeus_hotel_offers
        from mcp_tools.hotels.schemas import (
            HotelOffer,
            HotelRoomOption,
            MoneyAmount,
        )

        if self.should_fail:
            raise HotelProviderError("simulated provider failure")
        if self.malformed:
            raise HotelMalformedResponseError("simulated malformed response")
        if self.fixture_payload is not None:
            return parse_amadeus_hotel_offers(
                self.fixture_payload,
                request=request,
                location_name=request.location,
            )
        nightly = MoneyAmount(amount=Decimal("450.00"), currency=request.currency)
        total = MoneyAmount(amount=Decimal("2250.00"), currency=request.currency)
        return [
            HotelOffer(
                hotel_id="fake-hotel-1",
                name="Fake Marina Hotel",
                location=request.location,
                address="Marina Walk, Dubai, AE",
                latitude=25.0805,
                longitude=55.1403,
                room_options=[
                    HotelRoomOption(
                        room_type="Deluxe Room",
                        description="Deluxe room with marina view",
                        nightly_price=nightly,
                        total_price=total,
                    )
                ],
                nightly_price=nightly,
                total_price=total,
                check_in=request.check_in,
                check_out=request.check_out,
            )
        ]


class FakeLocationResolver:
    _MAPPINGS = {
        "mumbai": LocationPoint(name="Mumbai", latitude=19.076, longitude=72.8777),
        "dubai": LocationPoint(name="Dubai", latitude=25.2048, longitude=55.2708),
        "paris": LocationPoint(name="Paris", latitude=48.8566, longitude=2.3522),
    }

    def resolve(self, location: str) -> LocationPoint:
        from mcp_tools.distance.exceptions import LocationResolutionError

        normalized = location.strip().lower()
        point = self._MAPPINGS.get(normalized)
        if point is None:
            raise LocationResolutionError(f"location not found: {location}")
        return point


class FakeDistanceProvider:
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

    def get_distance_matrix(self, request):  # type: ignore[no-untyped-def]
        from mcp_tools.distance.exceptions import (
            DistanceMalformedResponseError,
            DistanceProviderError,
        )
        from mcp_tools.distance.providers.normalize import (
            build_identical_location_routes,
            parse_openrouteservice_matrix,
        )
        from mcp_tools.distance.schemas import DistanceRoute

        if self.should_fail:
            raise DistanceProviderError("simulated provider failure")
        if self.malformed:
            raise DistanceMalformedResponseError("simulated malformed response")
        if self.fixture_payload is not None:
            return parse_openrouteservice_matrix(
                self.fixture_payload,
                request=request,
            )

        routes: list[DistanceRoute] = []
        for origin in request.origins:
            for destination in request.destinations:
                if round(origin.latitude, 6) == round(
                    destination.latitude, 6
                ) and round(origin.longitude, 6) == round(destination.longitude, 6):
                    routes.append(
                        DistanceRoute(
                            origin=origin,
                            destination=destination,
                            distance_meters=0,
                            duration_seconds=0,
                            travel_mode=request.travel_mode,
                        )
                    )
                    continue
                routes.append(
                    DistanceRoute(
                        origin=origin,
                        destination=destination,
                        distance_meters=2_392_845,
                        duration_seconds=93_642,
                        travel_mode=request.travel_mode,
                    )
                )
        if not routes:
            return build_identical_location_routes(request)
        return routes


class FakePlacesProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        restaurant_payload: object | None = None,
        attraction_payload: object | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.restaurant_payload = restaurant_payload
        self.attraction_payload = attraction_payload

    def search_restaurants(self, request):  # type: ignore[no-untyped-def]
        from mcp_tools.places.exceptions import (
            PlacesMalformedResponseError,
            PlacesProviderError,
        )
        from mcp_tools.places.providers.normalize import parse_google_restaurant_places
        from mcp_tools.places.schemas import RestaurantPlace

        if self.should_fail:
            raise PlacesProviderError("simulated provider failure")
        if self.malformed:
            raise PlacesMalformedResponseError("simulated malformed response")
        if self.restaurant_payload is not None:
            return parse_google_restaurant_places(self.restaurant_payload)

        return [
            RestaurantPlace(
                place_id="places/ChIJfake-restaurant",
                name="Fake Restaurant",
                address="123 Test Street",
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                primary_type="restaurant",
                rating=4.2,
                user_rating_count=100,
            )
        ]

    def search_attractions(self, request):  # type: ignore[no-untyped-def]
        from mcp_tools.places.exceptions import (
            PlacesMalformedResponseError,
            PlacesProviderError,
        )
        from mcp_tools.places.providers.normalize import parse_google_attraction_places
        from mcp_tools.places.schemas import AttractionPlace

        if self.should_fail:
            raise PlacesProviderError("simulated provider failure")
        if self.malformed:
            raise PlacesMalformedResponseError("simulated malformed response")
        if self.attraction_payload is not None:
            return parse_google_attraction_places(self.attraction_payload)

        return [
            AttractionPlace(
                place_id="places/ChIJfake-attraction",
                name="Fake Attraction",
                address="456 Test Avenue",
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                primary_type="tourist_attraction",
                rating=4.6,
                user_rating_count=500,
            )
        ]


class FakeCurrencyRateProvider:
    def __init__(
        self,
        *,
        should_fail: bool = False,
        malformed: bool = False,
        rates: dict[tuple[str, str], Decimal] | None = None,
        fixture_payload: object | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.malformed = malformed
        self.rates = rates or {("USD", "INR"): Decimal("83.12")}
        self.fixture_payload = fixture_payload

    def get_exchange_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        rate_date=None,
    ):
        from datetime import date
        from decimal import Decimal

        from mcp_tools.currency.exceptions import (
            CurrencyMalformedResponseError,
            CurrencyProviderError,
        )
        from mcp_tools.currency.providers.base import ProviderExchangeRate
        from mcp_tools.currency.providers.normalize import parse_frankfurter_rate

        if self.should_fail:
            raise CurrencyProviderError("simulated provider failure")
        if self.malformed:
            raise CurrencyMalformedResponseError("simulated malformed response")
        if self.fixture_payload is not None:
            return parse_frankfurter_rate(
                self.fixture_payload,
                base_currency=base_currency,
                quote_currency=quote_currency,
            )

        base = base_currency.upper()
        quote = quote_currency.upper()
        rate = self.rates.get((base, quote))
        if rate is None:
            raise CurrencyProviderError(f"simulated missing rate for {base}/{quote}")
        return ProviderExchangeRate(
            base_currency=base,
            quote_currency=quote,
            rate=Decimal(str(rate)),
            rate_date=rate_date or date(2026, 3, 25),
        )
