"""DTOs for swipe-related use cases."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordSwipeInput:
    """Input for recording a swipe within a session."""

    session_id: str
    card_data: str  # serialized snapshot of the card the user acted on
    decision: str  # raw string, validated into SwipeDirection in the use case


@dataclass(frozen=True)
class RecordSwipeOutput:
    """Output after a swipe is recorded."""

    swipe_id: str
    interested: bool
