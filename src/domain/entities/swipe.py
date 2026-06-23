"""Swipe entity.

A single decision made during a swiping run. A swipe belongs to a session
and captures the card the user saw (``card_data``, an opaque serialized
snapshot) alongside the decision they made on it.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.exceptions import BusinessRuleViolation
from src.domain.value_objects.swipe_direction import SwipeDirection


class Swipe:
    """A single card decision recorded within a session."""

    def __init__(
        self,
        id: str,
        session_id: str,
        card_data: str,
        decision: SwipeDirection,
        created_at: Optional[datetime] = None,
    ) -> None:
        if not session_id:
            raise BusinessRuleViolation("Swipe must belong to a session")
        if not card_data:
            raise BusinessRuleViolation(
                "Swipe must capture the card it acted on"
            )

        self.id = id
        self.session_id = session_id
        self.card_data = card_data
        self.decision = decision
        self.created_at = created_at or datetime.utcnow()

    @property
    def is_interested(self) -> bool:
        return self.decision.is_positive
