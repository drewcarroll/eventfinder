"""DTOs for session lifecycle use cases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class StartSessionInput:
    """Input for opening a swiping session."""

    user_uid: str
    location: Optional[str] = None
    distance: Optional[float] = None
    time_range: Optional[str] = None


@dataclass(frozen=True)
class StartSessionOutput:
    """Output after a session is opened."""

    session_id: str


@dataclass(frozen=True)
class EndSessionInput:
    """Input for closing a swiping session."""

    session_id: str


@dataclass(frozen=True)
class EndSessionOutput:
    """Output after a session is closed."""

    session_id: str
    ended_at: datetime
    swipe_count: int
