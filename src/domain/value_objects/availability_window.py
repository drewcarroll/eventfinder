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
