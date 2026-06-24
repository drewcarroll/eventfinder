"""HTTP-level tests for the liked-ideas endpoints.

Drives the real FastAPI app through TestClient with a fake use-case factory
that simulates Firebase auth and stubbed use cases, so the endpoints'
wiring — auth, idea-key derivation, and serialization — is exercised
without any DB or network.
"""
import json

from fastapi.testclient import TestClient

from src.application.dtos.liked_idea_dtos import (
    DeleteLikedIdeaInput,
    LikeIdeaInput,
    LikeIdeaOutput,
    ListLikedIdeasInput,
    ListLikedIdeasOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

VALID_TOKEN = "good-token"
AUTH = {"Authorization": f"Bearer {VALID_TOKEN}"}


class StubLikeIdea:
    def __init__(self, recorder: list) -> None:
        self._recorder = recorder

    async def execute(self, dto: LikeIdeaInput) -> LikeIdeaOutput:
        self._recorder.append(dto)
        return LikeIdeaOutput(idea_id="idea-1")


class StubListLikedIdeas:
    def __init__(self, cards: list) -> None:
        self._cards = cards

    async def execute(
        self, dto: ListLikedIdeasInput
    ) -> ListLikedIdeasOutput:
        return ListLikedIdeasOutput(ideas=[json.dumps(c) for c in self._cards])


class StubDeleteLikedIdea:
    def __init__(self, recorder: list, missing: set | None = None) -> None:
        self._recorder = recorder
        self._missing = missing or set()

    async def execute(self, dto: DeleteLikedIdeaInput) -> None:
        self._recorder.append(dto)
        if dto.idea_key in self._missing:
            raise ResourceNotFoundError(
                f"Liked idea '{dto.idea_key}' not found"
            )


def _client(cards=None, missing=None) -> tuple[TestClient, list]:
    recorder: list = []

    async def factory(token: str) -> RequestScope:
        if token != VALID_TOKEN:
            raise PermissionError("Invalid authentication token")

        async def commit() -> None:
            return None

        return RequestScope(
            user_id="u1",
            get_event_feed=None,
            like_idea=StubLikeIdea(recorder),
            list_liked_ideas=StubListLikedIdeas(cards or []),
            delete_liked_idea=StubDeleteLikedIdea(recorder, missing),
            sync_user=None,
            resolve_location=None,
            search_locations=None,
            commit=commit,
        )

    return TestClient(create_app(use_case_factory=factory)), recorder


def test_like_requires_authentication():
    client, _ = _client()
    resp = client.post("/api/v1/likes", json={"card_data": {"id": "x"}})
    assert resp.status_code == 401


def test_like_records_idea_and_derives_key_from_id():
    client, recorder = _client()

    resp = client.post(
        "/api/v1/likes",
        json={"card_data": {"id": "farleys", "title": "Grab a drink"}},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert resp.json() == {"idea_id": "idea-1"}
    dto = recorder[0]
    assert dto.idea_key == "farleys"
    # The full card is snapshotted as JSON.
    assert json.loads(dto.card_data)["title"] == "Grab a drink"


def test_like_falls_back_to_title_when_no_id():
    client, recorder = _client()

    resp = client.post(
        "/api/v1/likes",
        json={"card_data": {"title": "Read a book at Cuesta Park"}},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert recorder[0].idea_key == "Read a book at Cuesta Park"


def test_like_rejects_card_without_id_or_title():
    client, _ = _client()

    resp = client.post(
        "/api/v1/likes",
        json={"card_data": {"category": "bar"}},
        headers=AUTH,
    )

    assert resp.status_code == 422


def test_list_returns_liked_idea_cards():
    cards = [
        {"id": "a", "title": "Grab a drink at Farley's"},
        {"id": "b", "title": "Read a book at Cuesta Park"},
    ]
    client, _ = _client(cards)

    resp = client.get("/api/v1/likes", headers=AUTH)

    assert resp.status_code == 200
    assert resp.json() == {"ideas": cards}


def test_delete_requires_authentication():
    client, _ = _client()
    resp = client.delete("/api/v1/likes/farleys")
    assert resp.status_code == 401


def test_delete_removes_liked_idea_scoped_to_user():
    client, recorder = _client()

    resp = client.delete("/api/v1/likes/farleys", headers=AUTH)

    assert resp.status_code == 204
    assert not resp.content
    dto = recorder[0]
    assert dto.user_uid == "u1"
    assert dto.idea_key == "farleys"


def test_delete_unknown_idea_returns_404():
    client, _ = _client(missing={"ghost"})

    resp = client.delete("/api/v1/likes/ghost", headers=AUTH)

    assert resp.status_code == 404
