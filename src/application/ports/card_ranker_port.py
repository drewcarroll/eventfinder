"""CardRankerPort.

Abstraction for ordering a pool of candidate cards into the sequence they
should be shown in the feed, backed by an LLM. Defined in the application
layer; implemented in infrastructure (e.g. Anthropic Claude). The use case
never knows which provider is used, and can fall back to its own
deterministic scoring when LLM ranking is unavailable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from src.domain.entities.event import Event
from src.domain.entities.user import User

# The requested feed time window as ``(starts_after, starts_before)``;
# either bound may be ``None`` to mean open-ended. Supplied to the ranker
# purely as context for its judgement.
TimeWindow = Tuple[Optional[datetime], Optional[datetime]]


class RankingUnavailableError(Exception):
    """Raised by a ranker when it cannot produce a usable ordering.

    Signals the caller to fall back to its own ranking rather than surface
    an empty or partial feed. Covers provider errors as well as unparseable
    or incomplete model output."""


class CardRankerPort(ABC):
    """Ranks and de-duplicates candidate cards for the feed."""

    @abstractmethod
    async def rank(
        self,
        cards: List[Event],
        user: User,
        window: Optional[TimeWindow] = None,
    ) -> List[Event]:
        """Return ``cards`` reordered best-first and de-duplicated.

        Judges each card on quality, novelty, and fit to the user's
        ``preferred_categories``; ``window`` is the requested feed time
        window, passed as context. Implementations MUST raise
        :class:`RankingUnavailableError` on any error or partial result —
        rather than returning a degraded list — so the caller can fall back
        to a deterministic ranking."""
