"""DTOs for swipe-related use cases."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordSwipeInput:
    """Input for recording a user's swipe decision."""

    user_id: str
    event_id: str
    direction: str  # raw string, validated into SwipeDirection in the use case


@dataclass(frozen=True)
class RecordSwipeOutput:
    """Output after a swipe is recorded."""

    swipe_id: str
    interested: bool
