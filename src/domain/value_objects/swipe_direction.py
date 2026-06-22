"""SwipeDirection value object.

Represents the immutable decision a user makes on an event card.
Equality is by value. The set of valid directions is a closed business
concept owned by the domain.
"""
from __future__ import annotations

from enum import Enum

from src.domain.exceptions import InvalidValueError


class SwipeDirection(str, Enum):
    """The direction a user swipes an event card."""

    LIKE = "like"
    PASS = "pass"
    SUPER_LIKE = "super_like"

    @classmethod
    def from_str(cls, raw: str) -> "SwipeDirection":
        """Build a SwipeDirection from raw input, validating the value."""
        try:
            return cls(raw.strip().lower())
        except ValueError as exc:
            valid = ", ".join(d.value for d in cls)
            raise InvalidValueError(
                f"'{raw}' is not a valid swipe direction. Expected one of: {valid}"
            ) from exc

    @property
    def is_positive(self) -> bool:
        """Whether this swipe expresses interest in the event."""
        return self in (SwipeDirection.LIKE, SwipeDirection.SUPER_LIKE)
