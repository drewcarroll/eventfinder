"""IdeaVerifierPort.

Abstraction for a final correctness gate on the feed: given the candidate
cards and the requested time window, confirm which ones a person could
*actually* do in that window — pruning anything that, by real-world
knowledge, isn't open or happening then (a museum at 1 AM, an event that
only runs on other days). Backed by an LLM; defined in the application
layer, implemented in infrastructure. The use case never knows the provider.

The deterministic ``CardFilter`` already drops cards whose self-reported
availability falls outside the window. This port adds judgement the filter
can't have: typical opening hours and whether a time-bound happening really
lands inside the window. It is best-effort — implementations MUST degrade by
returning the cards unchanged rather than emptying the feed when they cannot
produce a confident verdict.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from src.domain.entities.event import Event

# The requested feed window as ``(starts_after, starts_before)``; either
# bound may be ``None`` to mean open-ended.
TimeWindow = Tuple[Optional[datetime], Optional[datetime]]


class IdeaVerifierPort(ABC):
    """Prunes cards that aren't realistically doable in the time window."""

    @abstractmethod
    async def verify(
        self, cards: List[Event], window: TimeWindow
    ) -> List[Event]:
        """Return the subset of ``cards`` a person could actually do within
        ``window``, preserving the input order.

        Implementations degrade gracefully: on any provider error or
        unparseable response they return ``cards`` unchanged, so a flaky
        verifier never empties the feed."""
