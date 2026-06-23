"""HTTP-level tests for POST /sessions.

Drives the real FastAPI app through TestClient with a fake use-case factory
that simulates Firebase auth and a stubbed SaveSession use case, so the
endpoint's wiring — auth, body parsing, and the returned yes list — is
exercised without any DB, LLM, or network.
"""
from fastapi.testclient import TestClient

from src.application.dtos.session_dtos import (
    SaveSessionInput,
    SaveSessionOutput,
)
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

VALID_TOKEN = "good-token"
AUTH = {"Authorization": f"Bearer {VALID_TOKEN}"}


class StubSaveSession:
    """Stands in for the SaveSession use case at the HTTP boundary."""

    def __init__(self, output: SaveSessionOutput, recorder: list) -> None:
        self._output = output
        self._recorder = recorder

    async def execute(self, dto: SaveSessionInput) -> SaveSessionOutput:
        self._recorder.append(dto)
        return self._output


def _client(output: SaveSessionOutput) -> tuple[TestClient, list]:
    recorder: list = []

    async def factory(token: str) -> RequestScope:
        if token != VALID_TOKEN:
            raise PermissionError("Invalid authentication token")

        async def commit() -> None:
            return None

        return RequestScope(
            user_id="u1",
            get_event_feed=None,
            save_session=StubSaveSession(output, recorder),
            sync_user=None,
            resolve_location=None,
            commit=commit,
        )

    return TestClient(create_app(use_case_factory=factory)), recorder


def test_requires_authentication():
    client, _ = _client(SaveSessionOutput(session_id="s1", yes=[]))
    resp = client.post("/api/v1/sessions", json={"swipes": []})
    assert resp.status_code == 401


def test_saves_session_ties_to_user_and_returns_yes_list():
    liked = '{"id": "a", "title": "Jazz"}'
    client, recorder = _client(
        SaveSessionOutput(session_id="s1", yes=[liked])
    )

    resp = client.post(
        "/api/v1/sessions",
        headers=AUTH,
        json={
            "location": "Austin",
            "distance": 25,
            "time_range": "this weekend",
            "swipes": [
                {
                    "card_data": {"id": "a", "title": "Jazz"},
                    "decision": "like",
                },
                {"card_data": {"id": "b"}, "decision": "pass"},
            ],
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"] == "s1"
    # The compiled yes list comes back as parsed card objects.
    assert body["yes"] == [{"id": "a", "title": "Jazz"}]

    # The session is tied to the authenticated user, and swipe payloads
    # are forwarded to the use case as serialized card data.
    dto = recorder[0]
    assert dto.user_uid == "u1"
    assert dto.location == "Austin"
    assert len(dto.swipes) == 2
    assert dto.swipes[0].decision == "like"
