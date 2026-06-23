"""SQLAlchemy implementation of SwipeRepository."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.swipe import Swipe
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.value_objects.swipe_direction import SwipeDirection
from src.infrastructure.persistence.models import SessionModel, SwipeModel


class SqlSwipeRepository(SwipeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, swipe: Swipe) -> None:
        self._session.add(
            SwipeModel(
                id=swipe.id,
                session_id=swipe.session_id,
                card_data=swipe.card_data,
                decision=swipe.decision.value,
                created_at=swipe.created_at,
            )
        )
        await self._session.flush()

    async def list_for_session(self, session_id: str) -> List[Swipe]:
        result = await self._session.execute(
            select(SwipeModel)
            .where(SwipeModel.session_id == session_id)
            .order_by(SwipeModel.created_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_for_user(self, user_uid: str) -> List[Swipe]:
        result = await self._session.execute(
            select(SwipeModel)
            .join(SessionModel, SwipeModel.session_id == SessionModel.id)
            .where(SessionModel.user_uid == user_uid)
            .order_by(SwipeModel.created_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: SwipeModel) -> Swipe:
        return Swipe(
            id=model.id,
            session_id=model.session_id,
            card_data=model.card_data,
            decision=SwipeDirection(model.decision),
            created_at=model.created_at,
        )
