"""Amadeus OAuth2 token management."""

from __future__ import annotations

import time
from threading import Lock

import httpx

from mcp_tools.flights.exceptions import FlightProviderError, FlightProviderTimeoutError

AMADEUS_TOKEN_PATH = "/v1/security/oauth2/token"
TOKEN_REFRESH_BUFFER_SECONDS = 60


class AmadeusAuthClient:
    """Obtain and cache Amadeus API bearer tokens."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = Lock()

    def get_access_token(self) -> str:
        with self._lock:
            if self._token is not None and time.time() < self._expires_at:
                return self._token
            return self._refresh_token()

    def _refresh_token(self) -> str:
        url = f"{self._base_url}{AMADEUS_TOKEN_PATH}"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            if self._client is not None:
                response = self._client.post(
                    url,
                    data=data,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(url, data=data, headers=headers)
        except httpx.TimeoutException as exc:
            raise FlightProviderTimeoutError("amadeus auth request timed out") from exc
        except httpx.HTTPError as exc:
            raise FlightProviderError("amadeus auth request failed") from exc

        if response.status_code >= 400:
            raise FlightProviderError("amadeus auth request rejected")

        try:
            payload = response.json()
        except ValueError as exc:
            raise FlightProviderError("amadeus auth response was not JSON") from exc

        token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(token, str) or not isinstance(expires_in, int | float):
            raise FlightProviderError("amadeus auth response missing token fields")

        self._token = token
        self._expires_at = (
            time.time() + float(expires_in) - TOKEN_REFRESH_BUFFER_SECONDS
        )
        return self._token
