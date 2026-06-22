"""SQLAlchemy implementation of SwipeRepository."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.exceptions import ConflictError
from src.domain.entities.swipe import Swipe
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.value_objects.swipe_direction import SwipeDirection
from src.infrastructure.persistence.models import SwipeModel


class SqlSwipeRepository(SwipeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, swipe: Swipe) -> None:
        if await self.exists(swipe.user_id, swipe.event_id):
            # Re-throw infrastructure uniqueness as an application error.
            raise ConflictError("Swipe already exists for this user and event")
        self._session.add(
            SwipeModel(
                id=swipe.id,
                user_id=swipe.user_id,
                event_id=swipe.event_id,
                direction=swipe.direction.value,
                created_at=swipe.created_at,
            )
        )
        await self._session.flush()

    async def list_for_user(self, user_id: str) -> List[Swipe]:
        result = await self._session.execute(
            select(SwipeModel).where(SwipeModel.user_id == user_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def exists(self, user_id: str, event_id: str) -> bool:
        result = await self._session.execute(
            select(SwipeModel.id).where(
                SwipeModel.user_id == user_id,
                SwipeModel.event_id == event_id,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _to_entity(model: SwipeModel) -> Swipe:
        return Swipe(
            id=model.id,
            user_id=model.user_id,
            event_id=model.event_id,
            direction=SwipeDirection(model.direction),
            created_at=model.created_at,
        )
