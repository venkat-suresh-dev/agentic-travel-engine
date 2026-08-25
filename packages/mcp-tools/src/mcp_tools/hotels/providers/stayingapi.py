"""StayingAPI hotel search provider."""

from __future__ import annotations

import httpx

from mcp_tools.hotels.exceptions import (
    HotelMalformedResponseError,
    HotelProviderError,
    HotelProviderTimeoutError,
    HotelRateLimitError,
)
from mcp_tools.hotels.providers.stayingapi_normalize import parse_stayingapi_properties
from mcp_tools.hotels.schemas import HotelOffer, HotelSearchRequest

DEFAULT_STAYINGAPI_BASE_URL = "https://api.stayingapi.com"
STAYINGAPI_SEARCH_PATH = "/v1/search"


class StayingApiHotelProvider:
    """Search hotel properties via StayingAPI (sandbox or production)."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_STAYINGAPI_BASE_URL,
        environment: str = "sandbox",
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("StayingAPI API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._environment = environment
        self._timeout_seconds = timeout_seconds
        self._client = client

    @property
    def environment(self) -> str:
        return self._environment

    def search_hotels(self, request: HotelSearchRequest) -> list[HotelOffer]:
        params: dict[str, str | int] = {
            "location": request.location,
            "checkIn": request.check_in.isoformat(),
            "checkOut": request.check_out.isoformat(),
            "adults": request.travelers,
            "platforms": "booking",
            "currency": request.currency,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base_url}{STAYINGAPI_SEARCH_PATH}"

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
            payload = response.json()
        except ValueError as exc:
            raise HotelMalformedResponseError(
                "hotel search response was not JSON"
            ) from exc

        return parse_stayingapi_properties(payload, request=request)
