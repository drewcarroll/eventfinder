"""HTTP-level tests for GET /feed.

Drives the real FastAPI app through TestClient with a fake use-case factory
that simulates Firebase auth and a stubbed feed use case, so the endpoint's
wiring — auth, query parsing, ordering, and serialization — is exercised
without any DB, LLM, or network.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.application.dtos.event_dtos import (
    AvailabilityWindowDTO,
    EventDTO,
    GetEventFeedInput,
    GetEventFeedOutput,
)
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

VALID_TOKEN = "good-token"
AUTH = {"Authorization": f"Bearer {VALID_TOKEN}"}


class StubFeed:
    """Stands in for the GetEventFeed use case at the HTTP boundary."""

    def __init__(self, output: GetEventFeedOutput, recorder: list) -> None:
        self._output = output
        self._recorder = recorder

    async def execute(self, dto: GetEventFeedInput) -> GetEventFeedOutput:
        self._recorder.append(dto)
        return self._output


def _client(output: GetEventFeedOutput) -> tuple[TestClient, list]:
    """Build a TestClient whose factory authenticates VALID_TOKEN and
    returns a scope wrapping a StubFeed. Returns the captured-DTO list too."""
    recorder: list = []

    async def factory(token: str) -> RequestScope:
        if token != VALID_TOKEN:
            raise PermissionError("Invalid authentication token")

        async def commit() -> None:
            return None

        return RequestScope(
            user_id="u1",
            get_event_feed=StubFeed(output, recorder),
            like_idea=None,
            list_liked_ideas=None,
            sync_user=None,
            resolve_location=None,
            commit=commit,
        )

    return TestClient(create_app(use_case_factory=factory)), recorder


def _card(card_id: str, title: str, card_type: str = "event") -> EventDTO:
    return EventDTO(
        id=card_id,
        title=title,
        description="desc",
        category="music",
        starts_at=datetime(2030, 6, 15, 20, 0),
        source_url="https://example.com",
        latitude=30.27,
        longitude=-97.74,
        distance_km=1.5,
        card_type=card_type,
        availability_times=[
            AvailabilityWindowDTO(
                starts_at=datetime(2030, 6, 15, 18, 0),
                ends_at=datetime(2030, 6, 15, 22, 0),
            )
        ],
    )


def test_feed_requires_authentication():
    client, _ = _client(GetEventFeedOutput(events=[]))

    # Missing header, malformed header, and bad token are all rejected.
    missing = client.get("/api/v1/feed", params={"query": "music"})
    assert missing.status_code == 401
    assert (
        client.get(
            "/api/v1/feed",
            params={"query": "music"},
            headers={"Authorization": "Basic nope"},
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/feed",
            params={"query": "music"},
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )


def test_feed_returns_ordered_normalized_cards():
    output = GetEventFeedOutput(
        events=[
            _card("a", "Alpha", "event"),
            _card("b", "Beta", "activity"),
        ]
    )
    client, _ = _client(output)

    resp = client.get("/api/v1/feed", params={"query": "music"}, headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    # Order is preserved from the (already ranked) use-case output.
    assert [c["id"] for c in body["events"]] == ["a", "b"]
    first = body["events"][0]
    # Unified card schema fields are serialized.
    assert first["title"] == "Alpha"
    assert first["card_type"] == "event"
    assert first["latitude"] == 30.27
    assert first["distance_km"] == 1.5
    assert first["availability_times"] == [
        {
            "starts_at": "2030-06-15T18:00:00",
            "ends_at": "2030-06-15T22:00:00",
        }
    ]


def test_feed_accepts_location_distance_and_time_range():
    client, recorder = _client(GetEventFeedOutput(events=[]))

    resp = client.get(
        "/api/v1/feed",
        params={
            "query": "live music",
            "limit": 10,
            "latitude": 30.2672,
            "longitude": -97.7431,
            "radius_km": 25,
            "starts_after": "2030-06-10T00:00:00",
            "starts_before": "2030-06-20T00:00:00",
        },
        headers=AUTH,
    )

    assert resp.status_code == 200
    # The endpoint forwarded every filter into the use-case input.
    dto = recorder[0]
    assert dto.query == "live music"
    assert dto.limit == 10
    assert dto.latitude == 30.2672
    assert dto.longitude == -97.7431
    assert dto.radius_km == 25
    assert dto.starts_after == datetime(2030, 6, 10, 0, 0)
    assert dto.starts_before == datetime(2030, 6, 20, 0, 0)


def test_feed_returns_empty_list_cleanly():
    client, _ = _client(GetEventFeedOutput(events=[]))

    resp = client.get(
        "/api/v1/feed", params={"query": "nothing"}, headers=AUTH
    )

    assert resp.status_code == 200
    assert resp.json() == {"events": []}


@pytest.mark.parametrize("lat,lng", [(91, 0), (0, 181)])
def test_feed_rejects_out_of_range_coordinates(lat, lng):
    client, _ = _client(GetEventFeedOutput(events=[]))

    resp = client.get(
        "/api/v1/feed",
        params={"query": "music", "latitude": lat, "longitude": lng},
        headers=AUTH,
    )

    assert resp.status_code == 422
