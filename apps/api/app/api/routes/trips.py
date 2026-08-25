from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import TripOwnershipResponse
from app.auth.exceptions import AuthorizationError, ResourceNotFoundError
from app.core.current_user import CurrentUser
from app.db.session import get_db
from app.services.ownership import get_owned_trip

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/{trip_id}/ownership", response_model=TripOwnershipResponse)
async def verify_trip_ownership(
    trip_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TripOwnershipResponse:
    """Protected ownership probe for tests and future trip-scoped routes."""
    try:
        await get_owned_trip(db, trip_id=trip_id, current_user=current_user)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return TripOwnershipResponse(trip_id=trip_id, owned=True)
