"""HTTP-level tests for GET /users/me.

Drives the real FastAPI app through TestClient with a fake use-case factory
that simulates Firebase auth, so the endpoint's wiring — authentication,
user scoping, and serialization — is exercised without any DB or network.
"""
from datetime import datetime

from fastapi.testclient import TestClient

from src.application.dtos.user_dtos import (
    GetUserProfileInput,
    UserAccountOutput,
    UserStats,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

VALID_TOKEN = "good-token"
AUTH = {"Authorization": f"Bearer {VALID_TOKEN}"}


class StubGetUserProfile:
    """Returns an output for the requested uid, or raises if unknown."""

    def __init__(self, output, recorder: list) -> None:
        self._output = output
        self._recorder = recorder

    async def execute(self, dto: GetUserProfileInput) -> UserAccountOutput:
        self._recorder.append(dto)
        if self._output is None:
            raise ResourceNotFoundError(f"User {dto.uid} not found")
        return self._output


def _client(output, user_id: str = "u1") -> tuple[TestClient, list]:
    recorder: list = []

    async def factory(token: str) -> RequestScope:
        if token != VALID_TOKEN:
            raise PermissionError("Invalid authentication token")

        async def commit() -> None:
            return None

        return RequestScope(
            user_id=user_id,
            get_event_feed=None,
            save_session=None,
            sync_user=None,
            resolve_location=None,
            get_user_profile=StubGetUserProfile(output, recorder),
            commit=commit,
        )

    return TestClient(create_app(use_case_factory=factory)), recorder


def _account(uid: str = "u1") -> UserAccountOutput:
    return UserAccountOutput(
        uid=uid,
        email="a@b.com",
        username="BraveOtter42",
        name="Ada",
        preferred_activities="hikes, concerts",
        created_at=datetime(2030, 1, 1),
        stats=UserStats(sessions=2, liked_events=3, swipes=5),
    )


def test_requires_authentication():
    client, _ = _client(_account())
    assert client.get("/users/me").status_code == 401


def test_returns_profile_and_stats_for_authenticated_user():
    client, recorder = _client(_account())

    resp = client.get("/users/me", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["uid"] == "u1"
    assert body["username"] == "BraveOtter42"
    assert body["name"] == "Ada"
    assert body["preferred_activities"] == "hikes, concerts"
    assert body["stats"] == {
        "sessions": 2,
        "liked_events": 3,
        "swipes": 5,
    }


def test_scoped_to_the_authenticated_user():
    # The factory authenticates as "u42"; the endpoint must look up that
    # uid from the token, never anything supplied by the caller.
    client, recorder = _client(_account("u42"), user_id="u42")

    resp = client.get("/users/me", headers=AUTH)

    assert resp.status_code == 200
    assert recorder[0].uid == "u42"


def test_unknown_user_returns_404():
    client, _ = _client(None)
    assert client.get("/users/me", headers=AUTH).status_code == 404
