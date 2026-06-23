"""Use case tests for SaveSession.

No database, no HTTP, no LLM — only in-memory fakes that satisfy the
domain interfaces and application ports.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.session_dtos import (
    SaveSessionInput,
    SwipeDecisionInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.application.use_cases.save_session import SaveSession
from src.domain.entities.session import Session
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository


class FakeUserRepo(UserRepository):
    def __init__(self, users):
        self.users = {u.id: u for u in users}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FakeSessionRepo(SessionRepository):
    def __init__(self):
        self.sessions: dict[str, Session] = {}

    async def save(self, session: Session) -> None:
        self.sessions[session.id] = session

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)


class FakeSwipeRepo(SwipeRepository):
    def __init__(self):
        self.swipes: List[Swipe] = []

    async def save(self, swipe: Swipe) -> None:
        self.swipes.append(swipe)

    async def list_for_session(self, session_id) -> List[Swipe]:
        return [s for s in self.swipes if s.session_id == session_id]

    async def list_for_user(self, user_uid) -> List[Swipe]:
        return list(self.swipes)


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1)


class SequentialIds(IdGeneratorPort):
    def __init__(self):
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


def _build():
    users = FakeUserRepo([User(id="u1", email="a@b.com")])
    sessions = FakeSessionRepo()
    swipes = FakeSwipeRepo()
    use_case = SaveSession(
        users, sessions, swipes, SequentialIds(), FixedClock()
    )
    return use_case, sessions, swipes


@pytest.mark.asyncio
async def test_saves_session_and_swipes_and_returns_yes_list():
    use_case, sessions, swipes = _build()
    out = await use_case.execute(
        SaveSessionInput(
            user_uid="u1",
            location="Austin",
            distance=25.0,
            time_range="this weekend",
            swipes=[
                SwipeDecisionInput(card_data='{"id": "a"}', decision="like"),
                SwipeDecisionInput(card_data='{"id": "b"}', decision="pass"),
                SwipeDecisionInput(
                    card_data='{"id": "c"}', decision="super_like"
                ),
            ],
        )
    )

    # The session is persisted as a completed run (opened and closed).
    saved = sessions.sessions[out.session_id]
    assert saved.user_uid == "u1"
    assert saved.location == "Austin"
    assert not saved.is_active

    # Every decision is persisted...
    assert len(swipes.swipes) == 3
    # ...and only the positive ones are compiled into the yes list, in order.
    assert out.yes == ['{"id": "a"}', '{"id": "c"}']


@pytest.mark.asyncio
async def test_empty_session_saves_with_empty_yes_list():
    use_case, sessions, swipes = _build()
    out = await use_case.execute(SaveSessionInput(user_uid="u1"))
    assert out.yes == []
    assert len(swipes.swipes) == 0
    assert out.session_id in sessions.sessions


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found():
    use_case, _, _ = _build()
    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(SaveSessionInput(user_uid="ghost"))
