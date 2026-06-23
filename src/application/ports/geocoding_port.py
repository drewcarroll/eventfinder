"""GeocodingPort.

Abstraction for resolving a free-text place description (e.g. "Austin, TX")
into geographic coordinates. The application layer depends on this port; the
concrete adapter (a geocoding provider) lives in infrastructure. The use case
never knows which provider is used.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.domain.value_objects.geo_location import GeoLocation


@dataclass(frozen=True)
class GeocodingResult:
    """A resolved place: its coordinates plus a human-readable label."""

    location: GeoLocation
    display_name: str


class GeocodingPort(ABC):
    """Resolves free-text locations into coordinates."""

    @abstractmethod
    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        """Return the best match for ``query``, or ``None`` if unresolved."""
