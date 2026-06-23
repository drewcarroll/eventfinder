"""CardNormalizerPort.

Abstraction for turning raw web search results into normalized cards in
the unified schema, and for generating complementary activity cards — both
backed by an LLM. Defined in the application layer; implemented in
infrastructure (e.g. Anthropic Claude). The use case never knows which
provider is used.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

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
        self, query: str, user: User, limit: int
    ) -> List[Event]:
        """Generate up to ``limit`` activity cards relevant to the query and
        the user's tastes, in the unified schema."""
