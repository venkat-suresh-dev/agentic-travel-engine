"""Authentication package."""

from app.auth.clerk import AuthVerifier, ClerkAuthVerifier, build_auth_verifier
from app.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
)
from app.auth.types import AuthenticatedIdentity

__all__ = [
    "AuthenticatedIdentity",
    "AuthenticationError",
    "AuthVerifier",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ClerkAuthVerifier",
    "build_auth_verifier",
]
