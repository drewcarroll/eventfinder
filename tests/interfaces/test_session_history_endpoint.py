"""HTTP-level tests for GET /sessions and GET /sessions/{id}.

Drives the real FastAPI app through TestClient with a fake use-case factory
that simulates Firebase auth and stubbed history use cases, so the
endpoints' wiring — auth, user scoping, and serialization — is exercised
without any DB, LLM, or network.
"""
from datetime import datetime

from fastapi.testclient import TestClient

from src.application.dtos.session_dtos import (
    GetSessionDetailInput,
    ListSessionsInput,
    ListSessionsOutput,
    SessionDetailOutput,
    SessionSummaryOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

VALID_TOKEN = "good-token"
AUTH = {"Authorization": f"Bearer {VALID_TOKEN}"}


class StubListSessions:
    def __init__(self, output: ListSessionsOutput, recorder: list) -> None:
        self._output = output
        self._recorder = recorder

    async def execute(self, dto: ListSessionsInput) -> ListSessionsOutput:
        self._recorder.append(dto)
        return self._output


class StubGetSessionDetail:
    """Returns an output, or raises if the requested id is unknown."""

    def __init__(self, output, recorder: list) -> None:
        self._output = output
        self._recorder = recorder

    async def execute(self, dto: GetSessionDetailInput) -> SessionDetailOutput:
        self._recorder.append(dto)
        if self._output is None:
            raise ResourceNotFoundError(
                f"Session '{dto.session_id}' not found"
            )
        return self._output


def _client(list_output, detail_output) -> tuple[TestClient, list]:
    recorder: list = []

    async def factory(token: str) -> RequestScope:
        if token != VALID_TOKEN:
            raise PermissionError("Invalid authentication token")

        async def commit() -> None:
            return None

        return RequestScope(
            user_id="u1",
            get_event_feed=None,
            save_session=None,
            sync_user=None,
            resolve_location=None,
            list_sessions=StubListSessions(list_output, recorder),
            get_session_detail=StubGetSessionDetail(detail_output, recorder),
            commit=commit,
        )

    return TestClient(create_app(use_case_factory=factory)), recorder


def test_list_requires_authentication():
    client, _ = _client(ListSessionsOutput(sessions=[]), None)
    assert client.get("/api/v1/sessions").status_code == 401


def test_detail_requires_authentication():
    client, _ = _client(ListSessionsOutput(sessions=[]), None)
    assert client.get("/api/v1/sessions/s1").status_code == 401


def test_list_returns_sessions_scoped_to_user():
    output = ListSessionsOutput(
        sessions=[
            SessionSummaryOutput(
                session_id="s_new",
                location="Dallas",
                distance=10.0,
                time_range="tonight",
                created_at=datetime(2030, 2, 1),
                ended_at=datetime(2030, 2, 1),
                swipe_count=3,
                yes_count=2,
            ),
            SessionSummaryOutput(
                session_id="s_old",
                location="Austin",
                distance=None,
                time_range=None,
                created_at=datetime(2030, 1, 1),
                ended_at=datetime(2030, 1, 1),
                swipe_count=1,
                yes_count=0,
            ),
        ]
    )
    client, recorder = _client(output, None)

    resp = client.get("/api/v1/sessions", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert [s["session_id"] for s in body["sessions"]] == ["s_new", "s_old"]
    first = body["sessions"][0]
    assert first["location"] == "Dallas"
    assert first["swipe_count"] == 3
    assert first["yes_count"] == 2

    # The list is scoped to the authenticated user.
    assert recorder[0].user_uid == "u1"


def test_detail_returns_full_session_with_parsed_yes_list():
    output = SessionDetailOutput(
        session_id="s1",
        location="Austin",
        distance=25.0,
        time_range="this weekend",
        created_at=datetime(2030, 1, 1),
        ended_at=datetime(2030, 1, 1),
        swipe_count=2,
        yes=['{"id": "a", "title": "Jazz"}'],
    )
    client, recorder = _client(ListSessionsOutput(sessions=[]), output)

    resp = client.get("/api/v1/sessions/s1", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "s1"
    assert body["swipe_count"] == 2
    # The yes list comes back as parsed card objects.
    assert body["yes"] == [{"id": "a", "title": "Jazz"}]

    # The lookup is scoped to the authenticated user.
    dto = recorder[0]
    assert dto.user_uid == "u1"
    assert dto.session_id == "s1"


def test_detail_unknown_session_returns_404():
    client, _ = _client(ListSessionsOutput(sessions=[]), None)
    resp = client.get("/api/v1/sessions/ghost", headers=AUTH)
    assert resp.status_code == 404
