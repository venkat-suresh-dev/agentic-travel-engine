"""Amadeus airport and city code resolution."""

from __future__ import annotations

import httpx

from mcp_tools.flights.exceptions import (
    AirportResolutionError,
    FlightMalformedResponseError,
    FlightProviderError,
    FlightProviderTimeoutError,
)
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient

AMADEUS_LOCATIONS_PATH = "/v1/reference-data/locations"


class AmadeusAirportCodeResolver:
    """Resolve place names to IATA codes using Amadeus reference data."""

    def __init__(
        self,
        auth_client: AmadeusAuthClient,
        *,
        base_url: str,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._auth_client = auth_client
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def resolve(self, location: str) -> str:
        normalized = location.strip()
        if len(normalized) == 3 and normalized.isalpha():
            return normalized.upper()

        token = self._auth_client.get_access_token()
        params: dict[str, str | int] = {
            "keyword": normalized,
            "subType": "AIRPORT,CITY",
            "page[limit]": 1,
        }
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}{AMADEUS_LOCATIONS_PATH}"
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
            raise FlightProviderTimeoutError(
                "airport resolution request timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise FlightProviderError("airport resolution request failed") from exc

        if response.status_code >= 400:
            raise AirportResolutionError(f"location not found: {location}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise FlightMalformedResponseError(
                "airport resolution response was not JSON"
            ) from exc

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise AirportResolutionError(f"location not found: {location}")

        first = data[0]
        if not isinstance(first, dict):
            raise FlightMalformedResponseError("airport resolution entry invalid")

        iata = first.get("iataCode")
        if not isinstance(iata, str) or len(iata) != 3:
            raise AirportResolutionError(f"location not found: {location}")
        return iata.upper()
