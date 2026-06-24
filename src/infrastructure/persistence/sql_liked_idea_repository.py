"""SQLAlchemy implementation of LikedIdeaRepository."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.liked_idea import LikedIdea
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository
from src.infrastructure.persistence.models import LikedIdeaModel


class SqlLikedIdeaRepository(LikedIdeaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, idea: LikedIdea) -> None:
        # Liking the same idea again refreshes the existing record (its
        # snapshot and recency) rather than inserting a duplicate.
        result = await self._session.execute(
            select(LikedIdeaModel).where(
                LikedIdeaModel.user_uid == idea.user_uid,
                LikedIdeaModel.idea_key == idea.idea_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            self._session.add(self._to_model(idea))
        else:
            existing.card_data = idea.card_data
            existing.created_at = idea.created_at
        await self._session.flush()

    async def list_for_user(self, user_uid: str) -> List[LikedIdea]:
        result = await self._session.execute(
            select(LikedIdeaModel)
            .where(LikedIdeaModel.user_uid == user_uid)
            .order_by(LikedIdeaModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_model(idea: LikedIdea) -> LikedIdeaModel:
        return LikedIdeaModel(
            id=idea.id,
            user_uid=idea.user_uid,
            idea_key=idea.idea_key,
            card_data=idea.card_data,
            created_at=idea.created_at,
        )

    @staticmethod
    def _to_entity(model: LikedIdeaModel) -> LikedIdea:
        return LikedIdea(
            id=model.id,
            user_uid=model.user_uid,
            idea_key=model.idea_key,
            card_data=model.card_data,
            created_at=model.created_at,
        )
