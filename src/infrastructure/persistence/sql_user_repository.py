"""SQLAlchemy implementation of UserRepository.

Maps DB rows <-> domain entities. Implements the domain interface; the
application layer never sees these ORM models.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.persistence.models import UserModel


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        categories = ",".join(user.preferred_categories)
        if model is None:
            model = UserModel(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                username=user.username,
                preferred_categories=categories,
                preferred_activities=user.preferred_activities,
            )
            # Honor an explicit creation timestamp when provided; otherwise
            # the column's server default fills it in.
            if user.created_at is not None:
                model.created_at = user.created_at
            self._session.add(model)
        else:
            # created_at is immutable: never overwrite it on update.
            model.email = user.email
            model.display_name = user.display_name
            model.username = user.username
            model.preferred_categories = categories
            model.preferred_activities = user.preferred_activities
        await self._session.flush()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        categories = (
            [c for c in model.preferred_categories.split(",") if c]
            if model.preferred_categories
            else []
        )
        return User(
            id=model.id,
            email=model.email,
            display_name=model.display_name,
            preferred_categories=categories,
            created_at=model.created_at,
            username=model.username or "",
            preferred_activities=model.preferred_activities or "",
        )
