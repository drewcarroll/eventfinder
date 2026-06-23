"""SwipeRepository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.swipe import Swipe


class SwipeRepository(ABC):
    """Abstraction for persisting swipe decisions within sessions."""

    @abstractmethod
    async def save(self, swipe: Swipe) -> None:
        """Persist a swipe made within a session."""

    @abstractmethod
    async def list_for_session(self, session_id: str) -> List[Swipe]:
        """Return all swipes recorded in a session, oldest first."""

    @abstractmethod
    async def list_for_user(self, user_uid: str) -> List[Swipe]:
        """Return every swipe a user has made across all their sessions."""
