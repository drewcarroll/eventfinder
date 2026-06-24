"""Unit tests for the ResolveLocation use case.

Pure application-layer tests with a fake geocoder — no HTTP, no provider.
"""
from typing import Optional

import pytest

from src.application.dtos.location_dtos import ResolveLocationInput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.geocoding_port import (
    GeocodingPort,
    GeocodingResult,
)
from src.application.use_cases.resolve_location import ResolveLocation
from src.domain.value_objects.geo_location import GeoLocation


class FakeGeocoder(GeocodingPort):
    def __init__(self, result: Optional[GeocodingResult]) -> None:
        self._result = result
        self.queries: list[str] = []

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        self.queries.append(query)
        return self._result

    async def search(self, query: str, limit: int = 5):
        self.queries.append(query)
        return [self._result] if self._result is not None else []


@pytest.mark.asyncio
async def test_resolves_to_coordinates():
    geocoder = FakeGeocoder(
        GeocodingResult(
            location=GeoLocation(latitude=30.2672, longitude=-97.7431),
            display_name="Austin, Texas, USA",
        )
    )
    use_case = ResolveLocation(geocoder)

    out = await use_case.execute(ResolveLocationInput(query="Austin, TX"))

    assert out.latitude == 30.2672
    assert out.longitude == -97.7431
    assert out.display_name == "Austin, Texas, USA"
    assert geocoder.queries == ["Austin, TX"]


@pytest.mark.asyncio
async def test_trims_whitespace_before_geocoding():
    geocoder = FakeGeocoder(
        GeocodingResult(
            location=GeoLocation(latitude=1.0, longitude=2.0),
            display_name="Somewhere",
        )
    )
    use_case = ResolveLocation(geocoder)

    await use_case.execute(ResolveLocationInput(query="  Paris  "))

    assert geocoder.queries == ["Paris"]


@pytest.mark.asyncio
async def test_blank_query_raises_not_found():
    geocoder = FakeGeocoder(None)
    use_case = ResolveLocation(geocoder)

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(ResolveLocationInput(query="   "))

    # Should not even call the geocoder for an empty query.
    assert geocoder.queries == []


@pytest.mark.asyncio
async def test_unresolved_location_raises_not_found():
    geocoder = FakeGeocoder(None)
    use_case = ResolveLocation(geocoder)

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(
            ResolveLocationInput(query="Nowheresville XYZ123")
        )
