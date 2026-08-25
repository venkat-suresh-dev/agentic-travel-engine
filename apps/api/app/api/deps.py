"""FastAPI dependencies."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthVerifier, build_auth_verifier
from app.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
)
from app.core.config import settings
from app.core.current_user import CurrentUser
from app.db.models.trip import Trip
from app.db.session import get_db
from app.services.ownership import get_owned_trip as load_owned_trip
from app.services.users import resolve_or_create_user


@lru_cache
def get_auth_verifier() -> AuthVerifier:
    return build_auth_verifier(settings)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_verifier: Annotated[AuthVerifier, Depends(get_auth_verifier)],
) -> CurrentUser:
    try:
        identity = await auth_verifier.verify_request(request)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await resolve_or_create_user(db, identity)
    return CurrentUser.from_user(user)


async def get_owned_trip(
    trip_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Trip:
    try:
        return await load_owned_trip(db, trip_id=trip_id, current_user=current_user)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
