"""Use case tests for GetSessionDetail.

No database, no HTTP, no LLM — only in-memory fakes that satisfy the
domain interfaces.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.session_dtos import GetSessionDetailInput
from src.application.exceptions import ResourceNotFoundError
from src.application.use_cases.get_session_detail import GetSessionDetail
from src.domain.entities.session import Session
from src.domain.entities.swipe import Swipe
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.value_objects.swipe_direction import SwipeDirection


class FakeSessionRepo(SessionRepository):
    def __init__(self, sessions: List[Session]):
        self.sessions = {s.id: s for s in sessions}

    async def save(self, session: Session) -> None:
        self.sessions[session.id] = session

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    async def list_for_user(self, user_uid: str) -> List[Session]:
        return [s for s in self.sessions.values() if s.user_uid == user_uid]


class FakeSwipeRepo(SwipeRepository):
    def __init__(self, swipes: List[Swipe]):
        self.swipes = list(swipes)

    async def save(self, swipe: Swipe) -> None:
        self.swipes.append(swipe)

    async def list_for_session(self, session_id) -> List[Swipe]:
        return [s for s in self.swipes if s.session_id == session_id]

    async def list_for_user(self, user_uid) -> List[Swipe]:
        return list(self.swipes)


def _swipe(id: str, card_data: str, direction: SwipeDirection) -> Swipe:
    return Swipe(
        id=id,
        session_id="s1",
        card_data=card_data,
        decision=direction,
    )


@pytest.mark.asyncio
async def test_returns_detail_with_compiled_yes_list_in_order():
    sessions = FakeSessionRepo(
        [
            Session(
                id="s1",
                user_uid="u1",
                location="Austin",
                distance=25.0,
                time_range="this weekend",
                created_at=datetime(2030, 1, 1),
                ended_at=datetime(2030, 1, 1),
            )
        ]
    )
    swipes = FakeSwipeRepo(
        [
            _swipe("w1", '{"id": "a"}', SwipeDirection.LIKE),
            _swipe("w2", '{"id": "b"}', SwipeDirection.PASS),
            _swipe("w3", '{"id": "c"}', SwipeDirection.SUPER_LIKE),
        ]
    )
    use_case = GetSessionDetail(sessions=sessions, swipes=swipes)

    out = await use_case.execute(
        GetSessionDetailInput(user_uid="u1", session_id="s1")
    )

    assert out.session_id == "s1"
    assert out.location == "Austin"
    assert out.distance == 25.0
    assert out.swipe_count == 3
    # Only positive swipes, in swipe order.
    assert out.yes == ['{"id": "a"}', '{"id": "c"}']


@pytest.mark.asyncio
async def test_missing_session_raises_not_found():
    use_case = GetSessionDetail(
        sessions=FakeSessionRepo([]), swipes=FakeSwipeRepo([])
    )
    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(
            GetSessionDetailInput(user_uid="u1", session_id="ghost")
        )


@pytest.mark.asyncio
async def test_another_users_session_is_reported_not_found():
    sessions = FakeSessionRepo([Session(id="s1", user_uid="owner")])
    use_case = GetSessionDetail(
        sessions=sessions, swipes=FakeSwipeRepo([])
    )

    # Existence must not leak across users.
    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(
            GetSessionDetailInput(user_uid="intruder", session_id="s1")
        )
