"""Pydantic schemas for the liked-ideas HTTP boundary."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LikeIdeaRequest(BaseModel):
    """One idea the user swiped yes on.

    ``card_data`` is the full card snapshot (the same shape the feed
    returns). ``idea_key`` is an optional stable identity; when omitted the
    card's ``id`` is used so re-liking the same idea stays idempotent.
    """

    card_data: Dict[str, Any]
    idea_key: Optional[str] = None


class LikeIdeaResponse(BaseModel):
    idea_id: str


class LikedIdeasResponse(BaseModel):
    """A user's liked ideas, most recently liked first."""

    ideas: List[Dict[str, Any]]
