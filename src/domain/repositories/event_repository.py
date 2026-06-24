"""EventRepository interface.

Describes WHAT persistence operations the domain requires for events,
not HOW they are implemented. Implementations live in infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.event import Event


class EventRepository(ABC):
    """Abstraction for storing and retrieving Event entities."""

    @abstractmethod
    async def save(self, event: Event) -> None:
        """Persist (insert or update) an event."""

    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[Event]:
        """Return an event by id or None if it does not exist."""
