"""EventDiscoveryPort.

Abstraction for discovering events from external sources (e.g. Tavily web
search). The application layer depends on this port; the concrete adapter
lives in infrastructure. The use case never knows which provider is used.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from src.domain.entities.event import Event


@dataclass(frozen=True)
class DiscoveryQuery:
    """A request for candidate events: what to look for, near where, and
    within which time range.

    The application expresses *intent* here; the concrete adapter decides
    how to turn it into a provider-specific search. ``radius_km`` bounds
    proximity to the location named in ``query``; ``starts_after`` /
    ``starts_before`` bound the time range. ``None`` means "unconstrained"
    on that dimension.
    """

    query: str
    limit: int = 20
    radius_km: Optional[float] = None
    starts_after: Optional[datetime] = None
    starts_before: Optional[datetime] = None


class EventDiscoveryPort(ABC):
    """Discovers candidate events for a search query."""

    @abstractmethod
    async def discover(self, query: DiscoveryQuery) -> List[Event]:
        """Return raw candidate events as domain entities, ready for
        downstream normalization. Implementations degrade gracefully,
        returning an empty list when the provider is unavailable."""
