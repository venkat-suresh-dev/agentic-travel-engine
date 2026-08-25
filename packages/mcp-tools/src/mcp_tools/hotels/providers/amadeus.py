"""Amadeus hotel search provider."""

from __future__ import annotations

import httpx

from mcp_tools.flights.exceptions import (
    FlightProviderError,
    FlightProviderTimeoutError,
)
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient
from mcp_tools.hotels.exceptions import (
    HotelMalformedResponseError,
    HotelNoDataError,
    HotelProviderError,
    HotelProviderTimeoutError,
    HotelRateLimitError,
)
from mcp_tools.hotels.providers.normalize import (
    parse_amadeus_hotel_list,
    parse_amadeus_hotel_offers,
)
from mcp_tools.hotels.schemas import HotelOffer, HotelSearchRequest

AMADEUS_HOTEL_LIST_PATH = "/v1/reference-data/locations/hotels/by-city"
AMADEUS_HOTEL_OFFERS_PATH = "/v3/shopping/hotel-offers"
DEFAULT_AMADEUS_BASE_URL = "https://test.api.amadeus.com"
DEFAULT_HOTEL_LIST_LIMIT = 20


class AmadeusHotelProvider:
    """Search hotel offers via Amadeus Hotel List and Hotel Search APIs."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_AMADEUS_BASE_URL,
        timeout_seconds: float = 5.0,
        auth_client: AmadeusAuthClient | None = None,
        client: httpx.Client | None = None,
        hotel_list_limit: int = DEFAULT_HOTEL_LIST_LIMIT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._hotel_list_limit = hotel_list_limit
        self._auth_client = auth_client or AmadeusAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    def search_hotels(self, request: HotelSearchRequest) -> list[HotelOffer]:
        hotel_ids = self._list_hotel_ids(request.city_code)
        if not hotel_ids:
            raise HotelNoDataError("no hotels found for city")

        adults_per_room = (request.travelers + request.rooms - 1) // request.rooms
        params: dict[str, str | int] = {
            "hotelIds": ",".join(hotel_ids),
            "adults": adults_per_room,
            "roomQuantity": request.rooms,
            "checkInDate": request.check_in.isoformat(),
            "checkOutDate": request.check_out.isoformat(),
            "currency": request.currency,
        }

        payload = self._get(AMADEUS_HOTEL_OFFERS_PATH, params)
        return parse_amadeus_hotel_offers(
            payload,
            request=request,
            location_name=request.location,
        )

    def _list_hotel_ids(self, city_code: str) -> list[str]:
        payload = self._get(
            AMADEUS_HOTEL_LIST_PATH,
            {"cityCode": city_code},
        )
        hotel_ids = parse_amadeus_hotel_list(payload)
        return hotel_ids[: self._hotel_list_limit]

    def _get(self, path: str, params: dict[str, str | int]) -> object:
        try:
            token = self._auth_client.get_access_token()
        except FlightProviderTimeoutError as exc:
            raise HotelProviderTimeoutError("hotel auth request timed out") from exc
        except FlightProviderError as exc:
            raise HotelProviderError("hotel auth request failed") from exc

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}{path}"
        try:
            if self._client is not None:
                response = self._client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise HotelProviderTimeoutError("hotel search request timed out") from exc
        except httpx.HTTPError as exc:
            raise HotelProviderError("hotel search request failed") from exc

        if response.status_code == 429:
            raise HotelRateLimitError("hotel provider rate limited")
        if response.status_code >= 500:
            raise HotelProviderError("hotel provider unavailable")
        if response.status_code >= 400:
            raise HotelProviderError("hotel search request rejected")

        try:
            return response.json()
        except ValueError as exc:
            raise HotelMalformedResponseError(
                "hotel search response was not JSON"
            ) from exc
