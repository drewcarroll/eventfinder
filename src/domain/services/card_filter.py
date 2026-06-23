"""CardFilter domain service.

Applies the feed's spatial and temporal filters to a list of cards:

- distance: drop cards whose known location is beyond the maximum distance
  from the user's location;
- time range: drop cards with no availability inside the requested range.

Pure business logic — no I/O and no framework types. Time bounds are
expected in naive UTC, matching the convention used for stored card times.
A filter is skipped when the inputs it needs are absent (e.g. no user
location means distance cannot be — and is not — filtered).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.domain.entities.event import Event
from src.domain.value_objects.geo_location import GeoLocation


class CardFilter:
    """Filters cards by distance from the user and by availability."""

    def filter(
        self,
        cards: List[Event],
        *,
        origin: Optional[GeoLocation] = None,
        max_distance_km: Optional[float] = None,
        starts_after: Optional[datetime] = None,
        starts_before: Optional[datetime] = None,
    ) -> List[Event]:
        """Return only the cards that pass every active filter.

        Distance filtering requires both ``origin`` and ``max_distance_km``;
        time filtering activates when either bound is set, with the missing
        bound treated as open-ended.
        """
        apply_time = starts_after is not None or starts_before is not None
        start = starts_after or datetime.min
        end = starts_before or datetime.max

        result: List[Event] = []
        for card in cards:
            if origin is not None and max_distance_km is not None:
                if not card.is_within_distance(origin, max_distance_km):
                    continue
            if apply_time and not card.is_available_within(start, end):
                continue
            result.append(card)
        return result
