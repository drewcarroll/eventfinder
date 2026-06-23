"""Event entity.

An Event represents a real-world happening a user can swipe on.
It protects its own invariants in the constructor.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.exceptions import BusinessRuleViolation
from src.domain.value_objects.geo_location import GeoLocation


class Event:
    """A swipeable event with identity and lifecycle."""

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

    def is_upcoming(self, now: datetime) -> bool:
        """Business rule: an event is upcoming if it has not yet started."""
        return self.starts_at > now

    def starts_within(self, start: datetime, end: datetime) -> bool:
        """Business rule: the event begins within the inclusive
        ``[start, end]`` window."""
        return start <= self.starts_at <= end

    def matches_category(self, category: str) -> bool:
        return self.category.lower() == category.lower()
