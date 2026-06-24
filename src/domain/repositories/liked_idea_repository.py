"""LikedIdeaRepository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.liked_idea import LikedIdea


class LikedIdeaRepository(ABC):
    """Abstraction for persisting the ideas a user swiped yes on."""

    @abstractmethod
    async def save(self, idea: LikedIdea) -> None:
        """Persist a liked idea. Liking the same idea (same user +
        ``idea_key``) again refreshes the existing record rather than
        inserting a duplicate."""

    @abstractmethod
    async def list_for_user(self, user_uid: str) -> List[LikedIdea]:
        """Return a user's liked ideas, most recently liked first."""
