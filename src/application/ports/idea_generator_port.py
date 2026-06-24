"""IdeaGeneratorPort.

Abstraction for turning research material about an area into a large set of
concrete, single-idea swipe cards — backed by an LLM. Defined in the
application layer; implemented in infrastructure (e.g. Anthropic Claude).
The use case never knows which provider is used.

The contract is deliberately strict: every card returned must be ONE
specific, do-able idea ("Grab a drink at Farley's"), never a category or a
list ("Pubs near you"). Implementations split anything list-shaped into
separate cards and drop duplicates so the feed is a stream of distinct,
specific suggestions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.entities.event import Event
from src.domain.entities.user import User


class IdeaGeneratorPort(ABC):
    """Generates concrete, single-idea cards from research material."""

    @abstractmethod
    async def generate(
        self,
        query: str,
        user: User,
        limit: int,
        research: List[Event],
        starts_after: Optional[datetime] = None,
        starts_before: Optional[datetime] = None,
        radius_km: Optional[float] = None,
    ) -> List[Event]:
        """Return up to ``limit`` unique, specific, single-idea cards for the
        location described in ``query``, grounded in ``research`` (raw web
        results gathered for the area) and tailored to the user's tastes.

        ``starts_after``/``starts_before`` bound the time window the ideas
        must be available in, and ``radius_km`` bounds how far from the
        location they may be. ``None`` means "unconstrained" on that
        dimension. Implementations degrade gracefully, returning an empty
        list when generation is unavailable."""
