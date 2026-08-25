"""Amadeus city code resolution for hotel search."""

from __future__ import annotations

import httpx

from mcp_tools.flights.exceptions import (
    FlightProviderError,
    FlightProviderTimeoutError,
)
from mcp_tools.flights.providers.amadeus_auth import AmadeusAuthClient
from mcp_tools.hotels.exceptions import CityResolutionError

AMADEUS_LOCATIONS_PATH = "/v1/reference-data/locations"


class AmadeusCityCodeResolver:
    """Resolve place names to IATA city codes using Amadeus reference data."""

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
            "subType": "CITY",
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
        except FlightProviderTimeoutError as exc:
            raise CityResolutionError(f"city resolution timed out: {location}") from exc
        except FlightProviderError as exc:
            raise CityResolutionError(f"city resolution failed: {location}") from exc
        except httpx.TimeoutException as exc:
            raise CityResolutionError(f"city resolution timed out: {location}") from exc
        except httpx.HTTPError as exc:
            raise CityResolutionError(f"city resolution failed: {location}") from exc

        if response.status_code >= 400:
            raise CityResolutionError(f"location not found: {location}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise CityResolutionError(
                f"city resolution response invalid: {location}"
            ) from exc

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise CityResolutionError(f"location not found: {location}")

        first = data[0]
        if not isinstance(first, dict):
            raise CityResolutionError(f"city resolution response invalid: {location}")

        iata = first.get("iataCode")
        if not isinstance(iata, str) or len(iata) != 3:
            raise CityResolutionError(f"location not found: {location}")
        return iata.upper()
