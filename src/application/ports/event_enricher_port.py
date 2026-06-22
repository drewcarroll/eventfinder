"""EventEnricherPort.

Abstraction for enriching raw events with AI-generated summaries or
recommendations (e.g. via Anthropic Claude). Defined in the application
layer; implemented in infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.event import Event
from src.domain.entities.user import User


class EventEnricherPort(ABC):
    """Produces AI-enhanced descriptions tailored to a user."""

    @abstractmethod
    async def enrich(self, events: List[Event], user: User) -> List[Event]:
        """Return events with enriched descriptions. May be a no-op."""
