"""Amadeus flight offers search provider."""

from __future__ import annotations

import httpx

from mcp_tools.flights.exceptions import (
    FlightMalformedResponseError,
    FlightProviderError,
    FlightProviderTimeoutError,
    FlightRateLimitError,
)
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient
from mcp_tools.flights.providers.normalize import parse_amadeus_flight_offers
from mcp_tools.flights.schemas import CabinClass, FlightOffer, FlightSearchRequest

AMADEUS_FLIGHT_OFFERS_PATH = "/v2/shopping/flight-offers"
DEFAULT_AMADEUS_BASE_URL = "https://test.api.amadeus.com"

_CABIN_TO_TRAVEL_CLASS: dict[CabinClass, str] = {
    CabinClass.ECONOMY: "ECONOMY",
    CabinClass.PREMIUM_ECONOMY: "PREMIUM_ECONOMY",
    CabinClass.BUSINESS: "BUSINESS",
    CabinClass.FIRST: "FIRST",
}


class AmadeusFlightProvider:
    """Search flight offers via the Amadeus Flight Offers Search API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_AMADEUS_BASE_URL,
        timeout_seconds: float = 5.0,
        auth_client: AmadeusAuthClient | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._auth_client = auth_client or AmadeusAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    def search_flights(self, request: FlightSearchRequest) -> list[FlightOffer]:
        token = self._auth_client.get_access_token()
        params: dict[str, str | int] = {
            "originLocationCode": request.origin,
            "destinationLocationCode": request.destination,
            "departureDate": request.departure_date.isoformat(),
            "adults": request.travelers,
            "travelClass": _CABIN_TO_TRAVEL_CLASS[request.cabin_class],
            "currencyCode": request.currency,
            "max": 10,
        }
        if request.return_date is not None:
            params["returnDate"] = request.return_date.isoformat()

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}{AMADEUS_FLIGHT_OFFERS_PATH}"
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
            raise FlightProviderTimeoutError("flight search request timed out") from exc
        except httpx.HTTPError as exc:
            raise FlightProviderError("flight search request failed") from exc

        if response.status_code == 429:
            raise FlightRateLimitError("flight provider rate limited")
        if response.status_code >= 500:
            raise FlightProviderError("flight provider unavailable")
        if response.status_code >= 400:
            raise FlightProviderError("flight search request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise FlightMalformedResponseError(
                "flight search response was not JSON"
            ) from exc

        return parse_amadeus_flight_offers(payload, request=request)
