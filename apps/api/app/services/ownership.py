"""Trip ownership helpers."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import AuthorizationError, ResourceNotFoundError
from app.core.current_user import CurrentUser
from app.db.models.trip import Trip


async def get_owned_trip(
    db: AsyncSession,
    *,
    trip_id: UUID,
    current_user: CurrentUser,
) -> Trip:
    trip = await db.get(Trip, trip_id)
    if trip is None:
        raise ResourceNotFoundError("Trip not found")

    if trip.user_id != current_user.id:
        raise AuthorizationError("Trip does not belong to the authenticated user")

    return trip
