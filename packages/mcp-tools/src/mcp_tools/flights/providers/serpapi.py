"""SerpApi Google Flights search provider."""

from __future__ import annotations

import httpx

from mcp_tools.flights.exceptions import (
    FlightMalformedResponseError,
    FlightProviderError,
    FlightProviderTimeoutError,
    FlightRateLimitError,
)
from mcp_tools.flights.providers.serpapi_normalize import parse_serpapi_flight_offers
from mcp_tools.flights.schemas import CabinClass, FlightOffer, FlightSearchRequest

DEFAULT_SERPAPI_BASE_URL = "https://serpapi.com/search"
DEFAULT_SERPAPI_FLIGHTS_ENGINE = "google_flights"

_CABIN_TO_TRAVEL_CLASS: dict[CabinClass, str] = {
    CabinClass.ECONOMY: "economy",
    CabinClass.PREMIUM_ECONOMY: "premium_economy",
    CabinClass.BUSINESS: "business",
    CabinClass.FIRST: "first",
}


class SerpApiFlightProvider:
    """Search flight offers via SerpApi Google Flights engine."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_SERPAPI_BASE_URL,
        engine: str = DEFAULT_SERPAPI_FLIGHTS_ENGINE,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SerpApi API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._engine = engine
        self._timeout_seconds = timeout_seconds
        self._client = client

    def search_flights(self, request: FlightSearchRequest) -> list[FlightOffer]:
        params: dict[str, str | int] = {
            "engine": self._engine,
            "api_key": self._api_key,
            "departure_id": request.origin,
            "arrival_id": request.destination,
            "outbound_date": request.departure_date.isoformat(),
            "adults": request.travelers,
            "currency": request.currency,
            "travel_class": _CABIN_TO_TRAVEL_CLASS[request.cabin_class],
            "type": "2" if request.return_date is None else "1",
        }
        if request.return_date is not None:
            params["return_date"] = request.return_date.isoformat()

        try:
            if self._client is not None:
                response = self._client.get(
                    self._base_url,
                    params=params,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(self._base_url, params=params)
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

        return parse_serpapi_flight_offers(payload, request=request)
