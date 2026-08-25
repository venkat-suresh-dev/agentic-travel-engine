from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.trip import Trip


class ItineraryDay(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "itinerary_days"
    __table_args__ = (
        Index("ix_itinerary_days_trip_id", "trip_id"),
        UniqueConstraint(
            "trip_id",
            "day_index",
            name="uq_itinerary_days_trip_id_day_index",
        ),
    )

    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    trip: Mapped[Trip] = relationship(back_populates="itinerary_days")
    items: Mapped[list[ItineraryItem]] = relationship(
        back_populates="itinerary_day",
        cascade="all, delete-orphan",
        order_by="ItineraryItem.sort_order",
    )


class ItineraryItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "itinerary_items"
    __table_args__ = (
        Index(
            "ix_itinerary_items_itinerary_day_id_sort_order",
            "itinerary_day_id",
            "sort_order",
        ),
    )

    itinerary_day_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("itinerary_days.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    location: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    item_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    itinerary_day: Mapped[ItineraryDay] = relationship(back_populates="items")
