"""AvailabilityWindow value object.

An inclusive time window during which a card (event or activity) can be
attended. Immutable and validated by value, like all value objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.exceptions import InvalidValueError


@dataclass(frozen=True)
class AvailabilityWindow:
    """A bounded interval during which a card is available."""

    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.ends_at < self.starts_at:
            raise InvalidValueError(
                "availability window cannot end before it starts"
            )

    def overlaps(self, start: datetime, end: datetime) -> bool:
        """Whether this window intersects the inclusive ``[start, end]``
        range. This is what makes ``availability_times`` filterable by time
        range: a card is available within a requested range when any of its
        windows overlaps it."""
        return self.starts_at <= end and self.ends_at >= start
