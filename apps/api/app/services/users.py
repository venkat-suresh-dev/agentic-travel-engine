"""User synchronization for authenticated identities."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.types import AuthenticatedIdentity
from app.db.models.user import User


def _fallback_email(external_auth_id: str) -> str:
    return f"{external_auth_id}@users.clerk.local"


async def resolve_or_create_user(
    session: AsyncSession,
    identity: AuthenticatedIdentity,
) -> User:
    """Load or create the local user for a verified external identity."""
    stmt = select(User).where(User.external_auth_id == identity.external_auth_id)

    existing_user = await session.scalar(stmt)
    if existing_user is not None:
        return existing_user

    user = User(
        external_auth_id=identity.external_auth_id,
        email=identity.email or _fallback_email(identity.external_auth_id),
        display_name=identity.display_name,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raced_user = await session.scalar(stmt)
        if raced_user is None:
            raise
        return raced_user

    await session.refresh(user)
    return user
