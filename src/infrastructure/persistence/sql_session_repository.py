"""SQLAlchemy implementation of SessionRepository.

Maps DB rows <-> domain entities. The application layer never sees these
ORM models.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.session import Session
from src.domain.repositories.session_repository import SessionRepository
from src.infrastructure.persistence.models import SessionModel


class SqlSessionRepository(SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, session: Session) -> None:
        model = await self._session.get(SessionModel, session.id)
        if model is None:
            model = SessionModel(
                id=session.id,
                user_uid=session.user_uid,
                location=session.location,
                distance=session.distance,
                time_range=session.time_range,
                ended_at=session.ended_at,
            )
            # Honor an explicit start time when given; otherwise the column's
            # server default fills it in.
            if session.created_at is not None:
                model.created_at = session.created_at
            self._session.add(model)
        else:
            # Filters and created_at are fixed at start; only the close
            # timestamp changes over a session's life.
            model.ended_at = session.ended_at
        await self._session.flush()

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        model = await self._session.get(SessionModel, session_id)
        return self._to_entity(model) if model else None

    async def list_for_user(self, user_uid: str) -> List[Session]:
        result = await self._session.execute(
            select(SessionModel)
            .where(SessionModel.user_uid == user_uid)
            .order_by(SessionModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: SessionModel) -> Session:
        return Session(
            id=model.id,
            user_uid=model.user_uid,
            location=model.location,
            distance=model.distance,
            time_range=model.time_range,
            created_at=model.created_at,
            ended_at=model.ended_at,
        )
