"""RecommendationScorer domain service.

Pure business logic that ranks events for a user based on their swipe
history and preferred categories. Contains no I/O — it operates only on
domain entities and primitives.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from src.domain.entities.event import Event
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User


class RecommendationScorer:
    """Scores and ranks events according to domain rules."""

    CATEGORY_WEIGHT = 3.0
    POSITIVE_HISTORY_WEIGHT = 2.0
    UPCOMING_WEIGHT = 1.0

    def score(
        self,
        event: Event,
        user: User,
        history: List[Swipe],
        now: datetime,
    ) -> float:
        """Return a relevance score for an event. Higher is better."""
        score = 0.0

        if any(event.matches_category(c) for c in user.preferred_categories):
            score += self.CATEGORY_WEIGHT

        liked_categories = self._liked_category_counts(history, user)
        score += liked_categories.get(event.category.lower(), 0) * (
            self.POSITIVE_HISTORY_WEIGHT
        )

        if event.is_upcoming(now):
            score += self.UPCOMING_WEIGHT

        return score

    def rank(
        self,
        events: List[Event],
        user: User,
        history: List[Swipe],
        now: datetime,
    ) -> List[Event]:
        """Return events sorted by descending relevance score."""
        return sorted(
            events,
            key=lambda e: self.score(e, user, history, now),
            reverse=True,
        )

    @staticmethod
    def _liked_category_counts(
        history: List[Swipe], user: User
    ) -> Dict[str, int]:
        # Note: history only carries event ids; in this scorer we rely on
        # preferred_categories for category signal. The counts map is kept
        # as an extension point for richer signals.
        counts: Dict[str, int] = {}
        for category in user.preferred_categories:
            counts[category.lower()] = counts.get(category.lower(), 0) + 1
        positive = sum(1 for s in history if s.is_interested)
        if positive:
            for key in counts:
                counts[key] += 0  # placeholder for future weighting
        return counts
