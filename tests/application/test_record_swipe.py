"""Use case tests for the session swiping lifecycle.

No database, no HTTP, no LLM — only in-memory fakes that satisfy the
domain interfaces and application ports. This is the payoff of clean
architecture.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.session_dtos import (
    EndSessionInput,
    StartSessionInput,
)
from src.application.dtos.swipe_dtos import RecordSwipeInput
from src.application.exceptions import ConflictError, ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.application.use_cases.end_session import EndSession
from src.application.use_cases.record_swipe import RecordSwipe
from src.application.use_cases.start_session import StartSession
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
    ids = SequentialIds()
    clock = FixedClock()
    return {
        "users": users,
        "sessions": sessions,
        "swipes": swipes,
        "start": StartSession(users, sessions, ids, clock),
        "record": RecordSwipe(sessions, swipes, ids, clock),
        "end": EndSession(sessions, swipes, clock),
    }


@pytest.mark.asyncio
async def test_start_session_then_record_and_end():
    ctx = _build()
    started = await ctx["start"].execute(
        StartSessionInput(
            user_uid="u1",
            location="Austin",
            distance=25.0,
            time_range="this weekend",
        )
    )
    sid = started.session_id
    assert ctx["sessions"].sessions[sid].is_active

    out = await ctx["record"].execute(
        RecordSwipeInput(
            session_id=sid, card_data='{"id": "e1"}', decision="like"
        )
    )
    assert out.interested is True
    assert len(ctx["swipes"].swipes) == 1

    ended = await ctx["end"].execute(EndSessionInput(session_id=sid))
    assert ended.swipe_count == 1
    assert not ctx["sessions"].sessions[sid].is_active


@pytest.mark.asyncio
async def test_start_session_unknown_user_raises_not_found():
    ctx = _build()
    with pytest.raises(ResourceNotFoundError):
        await ctx["start"].execute(StartSessionInput(user_uid="ghost"))


@pytest.mark.asyncio
async def test_record_swipe_unknown_session_raises_not_found():
    ctx = _build()
    with pytest.raises(ResourceNotFoundError):
        await ctx["record"].execute(
            RecordSwipeInput(
                session_id="nope", card_data='{"id": "e1"}', decision="like"
            )
        )


@pytest.mark.asyncio
async def test_record_swipe_in_ended_session_raises_conflict():
    ctx = _build()
    started = await ctx["start"].execute(StartSessionInput(user_uid="u1"))
    await ctx["end"].execute(EndSessionInput(session_id=started.session_id))
    with pytest.raises(ConflictError):
        await ctx["record"].execute(
            RecordSwipeInput(
                session_id=started.session_id,
                card_data='{"id": "e1"}',
                decision="pass",
            )
        )
