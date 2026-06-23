"""ResolveLocation use case.

Turns a manually entered location (free text) into geographic coordinates
so it can override the user's GPS position for a session.

This use case knows WHAT to do, not HOW: it depends only on the geocoding
port and domain value objects — never on a concrete geocoding provider.
"""
from __future__ import annotations

from src.application.dtos.location_dtos import (
    ResolveLocationInput,
    ResolveLocationOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.geocoding_port import GeocodingPort


class ResolveLocation:
    """Resolve a free-text location into latitude/longitude."""

    def __init__(self, geocoder: GeocodingPort) -> None:
        self._geocoder = geocoder

    async def execute(
        self, dto: ResolveLocationInput
    ) -> ResolveLocationOutput:
        query = dto.query.strip()
        if not query:
            raise ResourceNotFoundError("No location provided to resolve")

        result = await self._geocoder.geocode(query)
        if result is None:
            raise ResourceNotFoundError(
                f"Could not resolve location '{query}'"
            )

        return ResolveLocationOutput(
            latitude=result.location.latitude,
            longitude=result.location.longitude,
            display_name=result.display_name,
        )
