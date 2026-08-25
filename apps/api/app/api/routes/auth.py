from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.schemas import UserResponse
from app.core.current_user import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    return current_user
