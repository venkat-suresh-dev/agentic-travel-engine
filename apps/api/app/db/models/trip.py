from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent_trace import AgentTrace
    from app.db.models.budget import Budget
    from app.db.models.itinerary import ItineraryDay
    from app.db.models.message import Message
    from app.db.models.tool_result import ToolResult
    from app.db.models.user import User


class Trip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trips"
    __table_args__ = (Index("ix_trips_user_id", "user_id"),)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    user: Mapped[User] = relationship(back_populates="trips")
    preferences: Mapped[list[TripPreference]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    tool_results: Mapped[list[ToolResult]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    itinerary_days: Mapped[list[ItineraryDay]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    budgets: Mapped[list[Budget]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    agent_traces: Mapped[list[AgentTrace]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )


class TripPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trip_preferences"
    __table_args__ = (
        Index("ix_trip_preferences_trip_id", "trip_id"),
        UniqueConstraint(
            "trip_id",
            "preference_key",
            name="uq_trip_preferences_trip_id_preference_key",
        ),
    )

    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    trip: Mapped[Trip] = relationship(back_populates="preferences")
