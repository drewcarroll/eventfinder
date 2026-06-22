"""GeoLocation value object.

Immutable latitude/longitude pair with validation of its invariants.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.exceptions import InvalidValueError


@dataclass(frozen=True)
class GeoLocation:
    """An immutable geographic coordinate."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise InvalidValueError(
                f"latitude must be between -90 and 90, got {self.latitude}"
            )
        if not -180.0 <= self.longitude <= 180.0:
            raise InvalidValueError(
                f"longitude must be between -180 and 180, got {self.longitude}"
            )
