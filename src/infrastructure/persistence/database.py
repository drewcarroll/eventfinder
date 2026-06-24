"""Async SQLAlchemy engine and session factory for PostgreSQL."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.infrastructure.config.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=_settings.debug)

SessionFactory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Schema is owned exclusively by Alembic migrations (``make migrate`` /
# ``alembic upgrade head``). The app no longer creates tables at startup:
# ``create_all`` only ever added *missing* tables and never altered existing
# ones, so it silently drifted from the models as the schema evolved.
