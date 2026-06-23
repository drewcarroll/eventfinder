"""Event entity.

An Event represents a real-world happening or activity a user can swipe
on — the unified "card" the feed is built from, regardless of whether it
originated as a web search result or a generated activity suggestion.
It protects its own invariants in the constructor.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.domain.exceptions import BusinessRuleViolation
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation

# The two kinds of card the feed merges into a single list.
CARD_TYPE_EVENT = "event"
CARD_TYPE_ACTIVITY = "activity"


class Event:
    """A swipeable card with identity and lifecycle."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        category: str,
        starts_at: datetime,
        source_url: str,
        location: Optional[GeoLocation] = None,
        ends_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        card_type: str = CARD_TYPE_EVENT,
        availability_times: Optional[List[AvailabilityWindow]] = None,
    ) -> None:
        if not id:
            raise BusinessRuleViolation("Event id is required")
        if not title or not title.strip():
            raise BusinessRuleViolation("Event title cannot be empty")
        if ends_at is not None and ends_at < starts_at:
            raise BusinessRuleViolation("Event cannot end before it starts")

        self.id = id
        self.title = title.strip()
        self.description = description
        self.category = category
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.source_url = source_url
        self.location = location
        self.image_url = image_url
        self.card_type = card_type
        self.availability_times: List[AvailabilityWindow] = (
            list(availability_times) if availability_times else []
        )

    def is_upcoming(self, now: datetime) -> bool:
        """Business rule: an event is upcoming if it has not yet started."""
        return self.starts_at > now

    def starts_within(self, start: datetime, end: datetime) -> bool:
        """Business rule: the event begins within the inclusive
        ``[start, end]`` window."""
        return start <= self.starts_at <= end

    def matches_category(self, category: str) -> bool:
        return self.category.lower() == category.lower()

    def identity_key(self) -> str:
        """A normalized key identifying the same real-world offering across
        sources. Two cards with the same key — e.g. a web result and a
        generated activity describing the same thing — are duplicates and
        collapse into one in the merged feed."""
        return " ".join(self.title.lower().split())

    def add_availability_windows(
        self, windows: List[AvailabilityWindow]
    ) -> None:
        """Fold additional availability windows in, ignoring exact
        duplicates so merging two views of the same card loses nothing."""
        for window in windows:
            if window not in self.availability_times:
                self.availability_times.append(window)
