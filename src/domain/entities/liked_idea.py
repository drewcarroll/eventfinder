"""LikedIdea entity.

An idea the user said "yes" to while swiping. Sessions no longer exist:
a like stands on its own, tying the user to an opaque snapshot of the card
they liked (``card_data``) and a stable ``idea_key`` so the same idea liked
again collapses onto the existing record rather than piling up duplicates.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.exceptions import BusinessRuleViolation


class LikedIdea:
    """One idea a user swiped yes on."""

    def __init__(
        self,
        id: str,
        user_uid: str,
        idea_key: str,
        card_data: str,
        created_at: Optional[datetime] = None,
    ) -> None:
        if not user_uid:
            raise BusinessRuleViolation("A liked idea must belong to a user")
        if not idea_key:
            raise BusinessRuleViolation("A liked idea must have an idea key")
        if not card_data:
            raise BusinessRuleViolation(
                "A liked idea must capture the card it acted on"
            )

        self.id = id
        self.user_uid = user_uid
        self.idea_key = idea_key
        self.card_data = card_data
        self.created_at = created_at or datetime.utcnow()
