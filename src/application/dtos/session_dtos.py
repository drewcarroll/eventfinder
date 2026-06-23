"""DTOs for saving and reading swiping sessions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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


@dataclass(frozen=True)
class ListSessionsInput:
    """Request to list a user's past sessions."""

    user_uid: str


@dataclass(frozen=True)
class SessionSummaryOutput:
    """Summary of one past session, for the history list."""

    session_id: str
    location: Optional[str]
    distance: Optional[float]
    time_range: Optional[str]
    created_at: datetime
    ended_at: Optional[datetime]
    swipe_count: int  # total decisions made this run
    yes_count: int  # how many of them expressed interest


@dataclass(frozen=True)
class ListSessionsOutput:
    """A user's past sessions, most recent first."""

    sessions: List[SessionSummaryOutput]


@dataclass(frozen=True)
class GetSessionDetailInput:
    """Request for one session's full detail, scoped to its owner."""

    user_uid: str
    session_id: str


@dataclass(frozen=True)
class SessionDetailOutput:
    """A single session's full detail, including the compiled yes list."""

    session_id: str
    location: Optional[str]
    distance: Optional[float]
    time_range: Optional[str]
    created_at: datetime
    ended_at: Optional[datetime]
    swipe_count: int
    yes: List[str]  # card_data of the cards swiped yes, in swipe order
