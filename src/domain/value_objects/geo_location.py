"""GeoLocation value object.

Immutable latitude/longitude pair with validation of its invariants.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.exceptions import InvalidValueError

# Mean Earth radius in kilometers (IUGG), used for great-circle distances.
_EARTH_RADIUS_KM = 6371.0088


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

    def distance_km_to(self, other: GeoLocation) -> float:
        """Great-circle distance in kilometers to ``other`` (haversine).

        This is the canonical computation behind a card's ``distance``
        field: how far the card is from the user's search origin. Pure
        math, no I/O."""
        lat1, lat2 = math.radians(self.latitude), math.radians(other.latitude)
        dlat = lat2 - lat1
        dlng = math.radians(other.longitude - self.longitude)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))
