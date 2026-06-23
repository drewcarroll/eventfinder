"""Use case tests for ListSessions.

No database, no HTTP, no LLM — only in-memory fakes that satisfy the
domain interfaces.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.session_dtos import ListSessionsInput
from src.application.use_cases.list_sessions import ListSessions
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
        # Most recent first, mirroring the SQL implementation's ordering.
        owned = [
            s for s in self.sessions.values() if s.user_uid == user_uid
        ]
        return sorted(owned, key=lambda s: s.created_at, reverse=True)


class FakeSwipeRepo(SwipeRepository):
    def __init__(self, swipes: List[Swipe]):
        self.swipes = list(swipes)

    async def save(self, swipe: Swipe) -> None:
        self.swipes.append(swipe)

    async def list_for_session(self, session_id) -> List[Swipe]:
        return [s for s in self.swipes if s.session_id == session_id]

    async def list_for_user(self, user_uid) -> List[Swipe]:
        return list(self.swipes)


def _swipe(session_id: str, direction: SwipeDirection) -> Swipe:
    return Swipe(
        id=f"{session_id}-{direction.value}",
        session_id=session_id,
        card_data='{"id": "x"}',
        decision=direction,
    )


@pytest.mark.asyncio
async def test_lists_sessions_most_recent_first_with_counts():
    sessions = FakeSessionRepo(
        [
            Session(
                id="s_old",
                user_uid="u1",
                location="Austin",
                created_at=datetime(2030, 1, 1),
                ended_at=datetime(2030, 1, 1),
            ),
            Session(
                id="s_new",
                user_uid="u1",
                location="Dallas",
                created_at=datetime(2030, 2, 1),
                ended_at=datetime(2030, 2, 1),
            ),
        ]
    )
    swipes = FakeSwipeRepo(
        [
            _swipe("s_old", SwipeDirection.LIKE),
            _swipe("s_old", SwipeDirection.PASS),
            _swipe("s_new", SwipeDirection.LIKE),
            _swipe("s_new", SwipeDirection.SUPER_LIKE),
        ]
    )
    use_case = ListSessions(sessions=sessions, swipes=swipes)

    out = await use_case.execute(ListSessionsInput(user_uid="u1"))

    # Most recent first.
    assert [s.session_id for s in out.sessions] == ["s_new", "s_old"]

    newest = out.sessions[0]
    assert newest.location == "Dallas"
    assert newest.swipe_count == 2
    assert newest.yes_count == 2  # like + super_like

    oldest = out.sessions[1]
    assert oldest.swipe_count == 2
    assert oldest.yes_count == 1  # only the like counts


@pytest.mark.asyncio
async def test_only_returns_the_callers_sessions():
    sessions = FakeSessionRepo(
        [
            Session(id="mine", user_uid="u1"),
            Session(id="theirs", user_uid="u2"),
        ]
    )
    use_case = ListSessions(sessions=sessions, swipes=FakeSwipeRepo([]))

    out = await use_case.execute(ListSessionsInput(user_uid="u1"))

    assert [s.session_id for s in out.sessions] == ["mine"]


@pytest.mark.asyncio
async def test_session_with_no_swipes_reports_zero_counts():
    sessions = FakeSessionRepo([Session(id="s1", user_uid="u1")])
    use_case = ListSessions(sessions=sessions, swipes=FakeSwipeRepo([]))

    out = await use_case.execute(ListSessionsInput(user_uid="u1"))

    assert out.sessions[0].swipe_count == 0
    assert out.sessions[0].yes_count == 0


@pytest.mark.asyncio
async def test_no_sessions_returns_empty_list():
    use_case = ListSessions(
        sessions=FakeSessionRepo([]), swipes=FakeSwipeRepo([])
    )
    out = await use_case.execute(ListSessionsInput(user_uid="u1"))
    assert out.sessions == []
