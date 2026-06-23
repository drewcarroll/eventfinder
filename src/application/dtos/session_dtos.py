"""DTOs for saving a completed swiping session."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class SwipeDecisionInput:
    """One decision made during the run."""

    card_data: str  # serialized snapshot of the card the user acted on
    decision: str  # raw string, validated into SwipeDirection in the use case


@dataclass(frozen=True)
class SaveSessionInput:
    """A completed swiping run to persist: the filters plus every decision."""

    user_uid: str
    location: Optional[str] = None
    distance: Optional[float] = None
    time_range: Optional[str] = None
    swipes: List[SwipeDecisionInput] = field(default_factory=list)


@dataclass(frozen=True)
class SaveSessionOutput:
    """Result of saving a session: its id and the compiled yes list."""

    session_id: str
    yes: List[str]  # card_data of the cards swiped yes, in swipe order
