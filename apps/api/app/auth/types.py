"""Provider-agnostic authenticated identity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """Verified identity from an external authentication provider."""

    external_auth_id: str
    email: str | None = None
    display_name: str | None = None
