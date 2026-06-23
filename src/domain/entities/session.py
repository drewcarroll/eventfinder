"""Session entity.

A swiping run: it opens when the user starts swiping, captures the filters
the feed was built from, and closes when the user is done. Swipes belong to
a session, so a closed session is a complete, saved record of one run.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.exceptions import BusinessRuleViolation


class Session:
    """One user's swiping run, scoped to the filters it was started with."""

    def __init__(
        self,
        id: str,
        user_uid: str,
        location: Optional[str] = None,
        distance: Optional[float] = None,
        time_range: Optional[str] = None,
        created_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
    ) -> None:
        if not user_uid:
            raise BusinessRuleViolation("Session must belong to a user")

        self.id = id
        self.user_uid = user_uid
        self.location = location
        self.distance = distance
        self.time_range = time_range
        self.created_at = created_at or datetime.utcnow()
        self.ended_at = ended_at

    @property
    def is_active(self) -> bool:
        """Whether the session is still open for swipes."""
        return self.ended_at is None

    def end(self, at: datetime) -> None:
        """Close the session. Ending an already-closed session is a no-op."""
        if self.ended_at is None:
            self.ended_at = at
