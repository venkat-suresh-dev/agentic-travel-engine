"""Build flight search requests from validated trip requirements."""

from __future__ import annotations

from datetime import date

from mcp_tools.flights.airports.base import AirportCodeResolver
from mcp_tools.flights.exceptions import FlightValidationError
from mcp_tools.flights.schemas import CabinClass, FlightSearchRequest

from app.domain.trip_request import TripRequest
from app.tools.weather_request import resolve_forecast_window


def resolve_departure_date(trip_request: TripRequest) -> date:
    """Derive the outbound departure date from validated trip schedule fields."""
    if trip_request.start_date:
        return trip_request.start_date
    return date.today()


def resolve_return_date(trip_request: TripRequest, departure_date: date) -> date | None:
    """Derive a return date when the trip request includes an explicit end date."""
    if trip_request.end_date and trip_request.end_date > departure_date:
        return trip_request.end_date
    if trip_request.start_date and trip_request.end_date:
        return trip_request.end_date
    return None


def build_flight_search_request(
    trip_request: TripRequest,
    airport_resolver: AirportCodeResolver,
) -> FlightSearchRequest:
    """Create a flight tool request from validated trip requirements."""
    if not trip_request.departure_city:
        raise FlightValidationError("departure_city is required for flight search")
    if not trip_request.destination:
        raise FlightValidationError("destination is required for flight search")
    if trip_request.travelers is None or trip_request.travelers < 1:
        raise FlightValidationError("travelers must be at least 1 for flight search")

    origin = airport_resolver.resolve(trip_request.departure_city)
    destination = airport_resolver.resolve(trip_request.destination)
    departure_date, _ = resolve_forecast_window(trip_request)
    if departure_date < date.today():
        departure_date = date.today()

    return_date = resolve_return_date(trip_request, departure_date)
    currency = (trip_request.budget_currency or "INR").upper()

    if return_date is not None and return_date < departure_date:
        raise FlightValidationError("return_date must be on or after departure_date")

    return FlightSearchRequest(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        travelers=trip_request.travelers,
        cabin_class=CabinClass.ECONOMY,
        currency=currency,
    )
