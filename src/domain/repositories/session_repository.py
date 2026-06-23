"""SessionRepository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.session import Session


class SessionRepository(ABC):
    """Abstraction for persisting swiping sessions."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Insert or update a session (used to open and to close it)."""

    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[Session]:
        """Return a session by its id, or None if it does not exist."""
