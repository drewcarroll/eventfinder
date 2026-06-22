"""UserRepository interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.user import User


class UserRepository(ABC):
    """Abstraction for storing and retrieving User entities."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Insert or update a user."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Return a user by Firebase UID or None."""
