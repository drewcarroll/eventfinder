"""SQLAlchemy ORM models.

ORM types live strictly inside infrastructure and are never leaked into
the application or domain layers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", server_default=""
    )
    # The real name the user optionally provides; null until they do.
    name: Mapped[Optional[str]] = mapped_column(String(255))
    preferred_categories: Mapped[str] = mapped_column(Text, default="")
    preferred_activities: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


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
    card_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="event", server_default="event"
    )
    # JSON-encoded list of {starts_at, ends_at} ISO 8601 windows.
    availability_times: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_uid: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id"), nullable=False
    )
    location: Mapped[Optional[str]] = mapped_column(String(512))
    distance: Mapped[Optional[float]] = mapped_column(Float)
    time_range: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class SwipeModel(Base):
    __tablename__ = "swipes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("sessions.id"), nullable=False
    )
    # Opaque serialized snapshot of the card the user acted on.
    card_data: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
