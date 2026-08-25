"""Build hotel search requests from validated trip requirements."""

from __future__ import annotations

from datetime import date, timedelta

from mcp_tools.hotels.exceptions import HotelValidationError
from mcp_tools.hotels.locations.base import CityCodeResolver
from mcp_tools.hotels.schemas import HotelSearchRequest

from app.domain.trip_request import TripRequest


def resolve_hotel_stay_window(trip_request: TripRequest) -> tuple[date, date]:
    """Derive hotel check-in and check-out dates from validated trip schedule fields."""
    if trip_request.start_date and trip_request.end_date:
        if trip_request.end_date <= trip_request.start_date:
            msg = "check_out must be after check_in"
            raise HotelValidationError(msg)
        return trip_request.start_date, trip_request.end_date
    if trip_request.start_date and trip_request.duration_days:
        check_out = trip_request.start_date + timedelta(days=trip_request.duration_days)
        return trip_request.start_date, check_out
    if trip_request.start_date:
        return trip_request.start_date, trip_request.start_date + timedelta(days=1)
    if trip_request.duration_days:
        today = date.today()
        return today, today + timedelta(days=trip_request.duration_days)
    today = date.today()
    return today, today + timedelta(days=1)


def resolve_room_count(trip_request: TripRequest) -> int:
    """Derive a conservative default room count from traveler count."""
    travelers = trip_request.travelers or 1
    return max(1, (travelers + 1) // 2)


def build_hotel_search_request(
    trip_request: TripRequest,
    city_resolver: CityCodeResolver,
) -> HotelSearchRequest:
    """Create a hotel tool request from validated trip requirements."""
    if not trip_request.destination:
        raise HotelValidationError("destination is required for hotel search")
    if trip_request.travelers is None or trip_request.travelers < 1:
        raise HotelValidationError("travelers must be at least 1 for hotel search")

    check_in, check_out = resolve_hotel_stay_window(trip_request)
    if check_in < date.today():
        check_in = date.today()
        if check_out <= check_in:
            check_out = check_in + timedelta(days=1)

    city_code = city_resolver.resolve(trip_request.destination)
    currency = (trip_request.budget_currency or "INR").upper()
    rooms = resolve_room_count(trip_request)

    return HotelSearchRequest(
        location=trip_request.destination,
        city_code=city_code,
        check_in=check_in,
        check_out=check_out,
        travelers=trip_request.travelers,
        rooms=rooms,
        currency=currency,
    )
