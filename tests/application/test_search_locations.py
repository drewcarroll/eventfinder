"""Unit tests for the SearchLocations use case.

Pure application-layer tests with a fake geocoder — no HTTP, no provider.
"""
from typing import List

import pytest

from src.application.dtos.location_dtos import SearchLocationsInput
from src.application.ports.geocoding_port import (
    GeocodingPort,
    GeocodingResult,
)
from src.application.use_cases.search_locations import SearchLocations
from src.domain.value_objects.geo_location import GeoLocation


class FakeGeocoder(GeocodingPort):
    def __init__(self, results: List[GeocodingResult]) -> None:
        self._results = results
        self.calls: list[tuple[str, int]] = []

    async def geocode(self, query: str):  # pragma: no cover - unused here
        return self._results[0] if self._results else None

    async def search(self, query: str, limit: int = 5):
        self.calls.append((query, limit))
        return list(self._results[:limit])


def _result(name: str, lat: float, lng: float) -> GeocodingResult:
    return GeocodingResult(
        location=GeoLocation(latitude=lat, longitude=lng),
        display_name=name,
    )


@pytest.mark.asyncio
async def test_maps_results_to_suggestions():
    geocoder = FakeGeocoder(
        [
            _result("San Francisco, California, USA", 37.77, -122.42),
            _result("San Jose, California, USA", 37.34, -121.89),
        ]
    )
    use_case = SearchLocations(geocoder)

    out = await use_case.execute(SearchLocationsInput(query="San ", limit=5))

    assert [s.display_name for s in out.suggestions] == [
        "San Francisco, California, USA",
        "San Jose, California, USA",
    ]
    assert out.suggestions[0].latitude == 37.77
    # Query is trimmed before being passed to the geocoder.
    assert geocoder.calls == [("San", 5)]


@pytest.mark.asyncio
async def test_short_query_returns_nothing_without_calling_geocoder():
    geocoder = FakeGeocoder([_result("Anywhere", 1.0, 2.0)])
    use_case = SearchLocations(geocoder)

    out = await use_case.execute(SearchLocationsInput(query="s"))

    assert out.suggestions == []
    assert geocoder.calls == []


@pytest.mark.asyncio
async def test_no_matches_returns_empty():
    geocoder = FakeGeocoder([])
    use_case = SearchLocations(geocoder)

    out = await use_case.execute(SearchLocationsInput(query="Zzzqq"))

    assert out.suggestions == []
