from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    service: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_auth_id: str
    email: str
    display_name: str | None


class TripOwnershipResponse(BaseModel):
    trip_id: UUID
    owned: bool
