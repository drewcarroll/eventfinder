"""RecommendationScorer domain service.

Pure business logic that ranks events for a user based on their preferred
categories and upcoming-ness. Contains no I/O — it operates only on domain
entities and primitives. Used as the deterministic fallback when the LLM
ranker is unavailable, so the feed degrades to a sensible order rather than
going empty.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from src.domain.entities.event import Event
from src.domain.entities.user import User


class RecommendationScorer:
    """Scores and ranks events according to domain rules."""

    CATEGORY_WEIGHT = 3.0
    UPCOMING_WEIGHT = 1.0

    def score(self, event: Event, user: User, now: datetime) -> float:
        """Return a relevance score for an event. Higher is better."""
        score = 0.0

        if any(event.matches_category(c) for c in user.preferred_categories):
            score += self.CATEGORY_WEIGHT

        if event.is_upcoming(now):
            score += self.UPCOMING_WEIGHT

        return score

    def rank(
        self, events: List[Event], user: User, now: datetime
    ) -> List[Event]:
        """Return events sorted by descending relevance score."""
        return sorted(
            events,
            key=lambda e: self.score(e, user, now),
            reverse=True,
        )
