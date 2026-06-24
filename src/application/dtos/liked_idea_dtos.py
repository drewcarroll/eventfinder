"""DTOs for liking ideas and reading a user's liked ideas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class LikeIdeaInput:
    """A single idea the user swiped yes on.

    ``idea_key`` is a stable identity for the idea (so re-liking the same
    idea doesn't pile up duplicates); ``card_data`` is the serialized
    snapshot of the card, kept so the idea survives without re-fetching.
    """

    user_uid: str
    idea_key: str
    card_data: str


@dataclass(frozen=True)
class LikeIdeaOutput:
    """Result of recording a like."""

    idea_id: str


@dataclass(frozen=True)
class ListLikedIdeasInput:
    """Request to list a user's liked ideas."""

    user_uid: str


@dataclass(frozen=True)
class ListLikedIdeasOutput:
    """A user's liked ideas, most recently liked first."""

    ideas: List[str]  # card_data snapshots, newest first
