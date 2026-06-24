"""Tests for the Nominatim geocoding adapter.

Uses httpx.MockTransport so the real request/response path runs without
hitting the network.
"""
import json

import httpx
import pytest

from src.infrastructure.geocoding.nominatim_geocoding import (
    NominatimGeocoding,
)


def _service(handler) -> NominatimGeocoding:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NominatimGeocoding(user_agent="test-agent", client=client)


@pytest.mark.asyncio
async def test_search_returns_multiple_us_city_candidates():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "37.7749",
                    "lon": "-122.4194",
                    "display_name": "San Francisco, California, USA",
                },
                {
                    "lat": "37.3382",
                    "lon": "-121.8863",
                    "display_name": "San Jose, California, USA",
                },
            ],
        )

    results = await _service(handler).search("San", limit=5)

    assert [r.display_name for r in results] == [
        "San Francisco, California, USA",
        "San Jose, California, USA",
    ]
    assert results[0].location.latitude == 37.7749
    # The type-ahead is biased to US places.
    assert captured["params"]["countrycodes"] == "us"
    assert captured["params"]["limit"] == "5"


@pytest.mark.asyncio
async def test_search_skips_candidates_with_bad_coordinates():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"lat": "not-a-number", "lon": "0", "display_name": "Bad"},
                {
                    "lat": "40.7128",
                    "lon": "-74.0060",
                    "display_name": "New York, USA",
                },
            ],
        )

    results = await _service(handler).search("New")
    assert [r.display_name for r in results] == ["New York, USA"]


@pytest.mark.asyncio
async def test_geocode_returns_the_top_search_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "30.2672",
                    "lon": "-97.7431",
                    "display_name": "Austin, Texas, USA",
                }
            ],
        )

    result = await _service(handler).geocode("Austin")
    assert result is not None
    assert result.display_name == "Austin, Texas, USA"
    assert result.location.latitude == 30.2672


@pytest.mark.asyncio
async def test_geocode_returns_none_when_no_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    assert await _service(handler).geocode("Nowhereville") is None
