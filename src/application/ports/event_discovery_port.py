"""EventDiscoveryPort.

Abstraction for discovering events from external sources (e.g. Tavily web
search). The application layer depends on this port; the concrete adapter
lives in infrastructure. The use case never knows which provider is used.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.event import Event


class EventDiscoveryPort(ABC):
    """Discovers candidate events for a search query."""

    @abstractmethod
    async def discover(self, query: str, limit: int) -> List[Event]:
        """Return events matching the query as domain entities."""
