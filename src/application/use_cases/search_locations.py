"""SearchLocations use case.

Powers the city type-ahead: turns the partial text a user has typed into a
short list of candidate places (name + coordinates) to choose from. Each
candidate already carries its coordinates, so picking one needs no second
round-trip to resolve it.

Knows WHAT to do, not HOW: it depends only on the geocoding port, never on a
concrete provider.
"""
from __future__ import annotations

from src.application.dtos.location_dtos import (
    LocationSuggestion,
    SearchLocationsInput,
    SearchLocationsOutput,
)
from src.application.ports.geocoding_port import GeocodingPort

# Below this many characters a type-ahead query is too broad to be useful (and
# wasteful to send), so we return nothing and let the user keep typing.
_MIN_QUERY_LENGTH = 2


class SearchLocations:
    """Suggest candidate places for a partial location query."""

    def __init__(self, geocoder: GeocodingPort) -> None:
        self._geocoder = geocoder

    async def execute(
        self, dto: SearchLocationsInput
    ) -> SearchLocationsOutput:
        query = dto.query.strip()
        if len(query) < _MIN_QUERY_LENGTH:
            return SearchLocationsOutput(suggestions=[])

        results = await self._geocoder.search(query, limit=dto.limit)
        return SearchLocationsOutput(
            suggestions=[
                LocationSuggestion(
                    latitude=r.location.latitude,
                    longitude=r.location.longitude,
                    display_name=r.display_name,
                )
                for r in results
            ]
        )
