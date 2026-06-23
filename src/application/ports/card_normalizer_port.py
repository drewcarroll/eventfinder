"""CardNormalizerPort.

Abstraction for turning raw web search results into normalized cards in
the unified schema, and for generating complementary activity cards — both
backed by an LLM. Defined in the application layer; implemented in
infrastructure (e.g. Anthropic Claude). The use case never knows which
provider is used.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.entities.event import Event
from src.domain.entities.user import User


class CardNormalizerPort(ABC):
    """Normalizes web results and generates activities as unified cards."""

    @abstractmethod
    async def normalize(self, raw: List[Event], user: User) -> List[Event]:
        """Return the raw web results rewritten into the unified card
        schema, populating ``availability_times`` where possible. May be a
        no-op if normalization is unavailable."""

    @abstractmethod
    async def generate_activities(
        self,
        query: str,
        user: User,
        limit: int,
        starts_after: Optional[datetime] = None,
        starts_before: Optional[datetime] = None,
        radius_km: Optional[float] = None,
    ) -> List[Event]:
        """Generate up to ``limit`` activity cards relevant to the query and
        the user's tastes, in the unified schema.

        ``starts_after``/``starts_before`` bound the time window the
        activities must be available in, and ``radius_km`` bounds how far
        from the location described in ``query`` they may be. ``None`` means
        "unconstrained" on that dimension. Implementations should steer
        generation toward cards whose ``availability_times`` fall inside the
        requested window and location radius."""
