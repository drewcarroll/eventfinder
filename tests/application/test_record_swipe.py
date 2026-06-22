"""Use case test demonstrating the application layer in full isolation.

No database, no HTTP, no LLM — only in-memory fakes that satisfy the
domain interfaces and application ports. This is the payoff of clean
architecture.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.swipe_dtos import RecordSwipeInput
from src.application.exceptions import ConflictError, ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.application.use_cases.record_swipe import RecordSwipe
from src.domain.entities.event import Event
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository


class FakeUserRepo(UserRepository):
    def __init__(self, users):
        self.users = {u.id: u for u in users}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FakeEventRepo(EventRepository):
    def __init__(self, events):
        self.events = {e.id: e for e in events}

    async def save(self, event: Event) -> None:
        self.events[event.id] = event

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        return self.events.get(event_id)

    async def list_unseen_for_user(self, user_id, limit) -> List[Event]:
        return list(self.events.values())[:limit]


class FakeSwipeRepo(SwipeRepository):
    def __init__(self):
        self.swipes: List[Swipe] = []

    async def save(self, swipe: Swipe) -> None:
        self.swipes.append(swipe)

    async def list_for_user(self, user_id) -> List[Swipe]:
        return [s for s in self.swipes if s.user_id == user_id]

    async def exists(self, user_id, event_id) -> bool:
        return any(
            s.user_id == user_id and s.event_id == event_id
            for s in self.swipes
        )


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1)


class FixedIds(IdGeneratorPort):
    def new_id(self) -> str:
        return "swipe-1"


def _build():
    user = User(id="u1", email="a@b.com")
    event = Event(
        id="e1",
        title="Jazz",
        description="",
        category="music",
        starts_at=datetime(2030, 6, 1),
        source_url="https://x.com",
    )
    users = FakeUserRepo([user])
    events = FakeEventRepo([event])
    swipes = FakeSwipeRepo()
    use_case = RecordSwipe(users, events, swipes, FixedIds(), FixedClock())
    return use_case, users, swipes


@pytest.mark.asyncio
async def test_record_like_persists_and_updates_preferences():
    use_case, users, swipes = _build()
    out = await use_case.execute(
        RecordSwipeInput(user_id="u1", event_id="e1", direction="like")
    )
    assert out.swipe_id == "swipe-1"
    assert out.interested is True
    assert len(swipes.swipes) == 1
    assert "music" in users.users["u1"].preferred_categories


@pytest.mark.asyncio
async def test_duplicate_swipe_raises_conflict():
    use_case, _, _ = _build()
    await use_case.execute(
        RecordSwipeInput(user_id="u1", event_id="e1", direction="like")
    )
    with pytest.raises(ConflictError):
        await use_case.execute(
            RecordSwipeInput(user_id="u1", event_id="e1", direction="pass")
        )


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found():
    use_case, _, _ = _build()
    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(
            RecordSwipeInput(user_id="ghost", event_id="e1", direction="like")
        )
