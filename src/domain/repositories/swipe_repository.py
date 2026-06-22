"""SwipeRepository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.swipe import Swipe


class SwipeRepository(ABC):
    """Abstraction for persisting user swipe decisions."""

    @abstractmethod
    async def save(self, swipe: Swipe) -> None:
        """Persist a swipe. Must enforce one swipe per (user, event)."""

    @abstractmethod
    async def list_for_user(self, user_id: str) -> List[Swipe]:
        """Return all swipes made by a user."""

    @abstractmethod
    async def exists(self, user_id: str, event_id: str) -> bool:
        """Whether the user has already swiped on the event."""
