"""Clerk token verification."""

from typing import Protocol

from fastapi import Request

from app.auth.exceptions import AuthenticationError
from app.auth.types import AuthenticatedIdentity
from app.core.config import Settings


class AuthVerifier(Protocol):
    """Provider-agnostic authentication boundary."""

    async def verify_request(self, request: Request) -> AuthenticatedIdentity:
        """Verify the incoming request and return the authenticated identity."""


class ClerkAuthVerifier:
    """Verify Clerk session tokens using the official Clerk backend SDK."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def verify_request(self, request: Request) -> AuthenticatedIdentity:
        from clerk_backend_api.security import (
            AuthenticateRequestOptions,
            authenticate_request_async,
        )

        if not self._settings.clerk_secret_key:
            raise AuthenticationError("Clerk is not configured")

        state = await authenticate_request_async(
            request,
            AuthenticateRequestOptions(
                secret_key=self._settings.clerk_secret_key,
                jwt_key=self._settings.clerk_jwt_key,
                authorized_parties=self._settings.clerk_authorized_parties,
                accepts_token=["session_token"],
            ),
        )

        if not state.is_signed_in:
            reason = state.reason.name if state.reason else "unauthorized"
            raise AuthenticationError(reason)

        payload = state.payload or {}
        external_auth_id = payload.get("sub")
        if not external_auth_id:
            raise AuthenticationError("missing subject claim")

        display_name = payload.get("name")
        if display_name is None:
            first_name = payload.get("first_name")
            last_name = payload.get("last_name")
            if first_name or last_name:
                display_name = " ".join(
                    part for part in [first_name, last_name] if part
                )

        return AuthenticatedIdentity(
            external_auth_id=external_auth_id,
            email=payload.get("email"),
            display_name=display_name,
        )


def build_auth_verifier(settings: Settings) -> AuthVerifier:
    return ClerkAuthVerifier(settings)
