"""Fake hotel providers for API integration tests."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.hotels.exceptions import (
    CityResolutionError,
    HotelMalformedResponseError,
    HotelProviderError,
)
from mcp_tools.hotels.schemas import (
    HotelOffer,
    HotelRoomOption,
    HotelSearchRequest,
    MoneyAmount,
)


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
            raise CityResolutionError(f"location not found: {location}")
        return code


class FakeHotelProvider:
    def __init__(self, *, should_fail: bool = False, malformed: bool = False) -> None:
        self.should_fail = should_fail
        self.malformed = malformed

    def search_hotels(self, request: HotelSearchRequest) -> list[HotelOffer]:
        if self.should_fail:
            raise HotelProviderError("simulated provider failure")
        if self.malformed:
            raise HotelMalformedResponseError("simulated malformed response")
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
            ),
            HotelOffer(
                hotel_id="fake-hotel-2",
                name="Fake Creek Hotel",
                location=request.location,
                address="Al Fahidi, Dubai, AE",
                latitude=25.2630,
                longitude=55.2970,
                room_options=[
                    HotelRoomOption(
                        room_type="Standard Room",
                        description="Standard room near the creek",
                        nightly_price=MoneyAmount(
                            amount=Decimal("620.00"), currency=request.currency
                        ),
                        total_price=MoneyAmount(
                            amount=Decimal("3100.00"), currency=request.currency
                        ),
                    )
                ],
                nightly_price=MoneyAmount(
                    amount=Decimal("620.00"), currency=request.currency
                ),
                total_price=MoneyAmount(
                    amount=Decimal("3100.00"), currency=request.currency
                ),
                check_in=request.check_in,
                check_out=request.check_out,
            ),
        ]
