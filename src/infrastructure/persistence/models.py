"""SQLAlchemy ORM models.

ORM types live strictly inside infrastructure and are never leaked into
the application or domain layers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    preferred_categories: Mapped[str] = mapped_column(Text, default="")


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(128), default="general")
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source_url: Mapped[str] = mapped_column(String(2048), default="")
    image_url: Mapped[Optional[str]] = mapped_column(String(2048))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)


class SwipeModel(Base):
    __tablename__ = "swipes"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event_swipe"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("events.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
