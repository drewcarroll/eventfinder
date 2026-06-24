"""Tests for the Tavily discovery adapter.

Uses httpx.MockTransport so the real httpx request/response path (including
raise_for_status) runs without hitting the network.
"""
import hashlib
import json
from datetime import datetime

import httpx
import pytest

from src.application.ports.event_discovery_port import DiscoveryQuery
from src.infrastructure.discovery.tavily_event_discovery import (
    TavilyEventDiscovery,
)


def _service(handler) -> TavilyEventDiscovery:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TavilyEventDiscovery(api_key="test-key", client=client)


@pytest.mark.asyncio
async def test_maps_results_to_events():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Jazz Night",
                        "url": "https://example.com/jazz",
                        "content": "Live jazz downtown",
                    },
                    {
                        "title": "Food Festival",
                        "url": "https://example.com/food",
                        "content": "Tacos galore",
                    },
                ]
            },
        )

    service = _service(handler)
    events = await service.discover(DiscoveryQuery(query="music", limit=5))

    assert [e.title for e in events] == ["Jazz Night", "Food Festival"]
    assert events[0].source_url == "https://example.com/jazz"
    assert events[0].description == "Live jazz downtown"
    # ID is a stable hash of the source URL.
    assert events[0].id == hashlib.sha1(
        b"https://example.com/jazz"
    ).hexdigest()


@pytest.mark.asyncio
async def test_skips_results_missing_title_or_url():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "", "url": "https://example.com/a"},
                    {"title": "No URL", "url": ""},
                    {"title": "Good", "url": "https://example.com/good"},
                ]
            },
        )

    events = await _service(handler).discover(DiscoveryQuery(query="x"))
    assert [e.title for e in events] == ["Good"]


@pytest.mark.asyncio
async def test_query_includes_location_radius_and_time_range():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"results": []})

    await _service(handler).discover(
        DiscoveryQuery(
            query="live music near Austin",
            limit=7,
            radius_km=25,
            starts_after=datetime(2030, 6, 10, 9, 0),
            starts_before=datetime(2030, 6, 20, 18, 0),
        )
    )

    built = captured["payload"]["query"]
    assert "live music near Austin" in built
    assert "within 25 km" in built
    assert "between 2030-06-10 and 2030-06-20" in built
    assert captured["payload"]["max_results"] == 7


@pytest.mark.asyncio
async def test_same_day_window_searches_today_or_tonight():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"results": []})

    # A "what can I do today?" window: now until the early hours of the next
    # morning. Narrow windows bias the search toward what's happening now
    # rather than scattering across future dates.
    await _service(handler).discover(
        DiscoveryQuery(
            query="things to do near Austin",
            starts_after=datetime(2030, 6, 15, 20, 0),
            starts_before=datetime(2030, 6, 16, 4, 0),
        )
    )

    built = captured["payload"]["query"]
    assert "happening today or tonight on 2030-06-15" in built
    assert "between" not in built


@pytest.mark.asyncio
async def test_returns_empty_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream boom")

    events = await _service(handler).discover(DiscoveryQuery(query="x"))
    assert events == []


@pytest.mark.asyncio
async def test_returns_empty_on_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    events = await _service(handler).discover(DiscoveryQuery(query="x"))
    assert events == []


@pytest.mark.asyncio
async def test_returns_empty_on_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    events = await _service(handler).discover(DiscoveryQuery(query="x"))
    assert events == []


@pytest.mark.asyncio
async def test_skips_discovery_when_no_api_key():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("API should not be called without a key")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = TavilyEventDiscovery(api_key="", client=client)

    assert await service.discover(DiscoveryQuery(query="x")) == []
