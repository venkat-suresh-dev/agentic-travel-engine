"""Application user representations for authenticated requests."""

from dataclasses import dataclass
from uuid import UUID

from app.db.models.user import User


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Provider-agnostic authenticated application user."""

    id: UUID
    external_auth_id: str
    email: str
    display_name: str | None

    @classmethod
    def from_user(cls, user: User) -> "CurrentUser":
        if user.external_auth_id is None:
            msg = "Authenticated user is missing external_auth_id"
            raise ValueError(msg)
        return cls(
            id=user.id,
            external_auth_id=user.external_auth_id,
            email=user.email,
            display_name=user.display_name,
        )
