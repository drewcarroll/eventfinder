"""Swipe entity.

Records a user's decision about an event. The combination of a user and
an event must be unique — a rule enforced by the repository, but the
entity guarantees the integrity of its own fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.exceptions import BusinessRuleViolation
from src.domain.value_objects.swipe_direction import SwipeDirection


class Swipe:
    """A single user decision on an event."""

    def __init__(
        self,
        id: str,
        user_id: str,
        event_id: str,
        direction: SwipeDirection,
        created_at: Optional[datetime] = None,
    ) -> None:
        if not user_id:
            raise BusinessRuleViolation("Swipe must belong to a user")
        if not event_id:
            raise BusinessRuleViolation("Swipe must reference an event")

        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.direction = direction
        self.created_at = created_at or datetime.utcnow()

    @property
    def is_interested(self) -> bool:
        return self.direction.is_positive
