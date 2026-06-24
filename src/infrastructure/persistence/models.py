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
    UniqueConstraint,
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


class LikedIdeaModel(Base):
    __tablename__ = "liked_ideas"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_uid: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id"), nullable=False
    )
    # Stable identity for the idea, so re-liking it doesn't duplicate.
    idea_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # Opaque serialized snapshot of the card the user liked.
    card_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_uid", "idea_key", name="uq_user_idea"),
    )
