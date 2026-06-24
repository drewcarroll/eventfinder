"""Unit tests for the GetUserProfile use case.

Pure application-layer tests with in-memory fake repositories — no
database, no HTTP. Verifies the profile is returned with activity stats
compiled from the user's sessions and swipes.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.user_dtos import GetUserProfileInput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.use_cases.get_user_profile import GetUserProfile
from src.domain.entities.session import Session
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.value_objects.swipe_direction import SwipeDirection


class FakeUserRepo(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FakeSessionRepo(SessionRepository):
    def __init__(self, sessions: List[Session]) -> None:
        self._sessions = sessions

    async def save(self, session: Session) -> None:  # pragma: no cover
        self._sessions.append(session)

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        return next(
            (s for s in self._sessions if s.id == session_id), None
        )

    async def list_for_user(self, user_uid: str) -> List[Session]:
        return [s for s in self._sessions if s.user_uid == user_uid]


class FakeSwipeRepo(SwipeRepository):
    def __init__(self, swipes: List[Swipe]) -> None:
        self._swipes = swipes

    async def save(self, swipe: Swipe) -> None:  # pragma: no cover
        self._swipes.append(swipe)

    async def list_for_session(self, session_id: str) -> List[Swipe]:
        return [s for s in self._swipes if s.session_id == session_id]

    async def list_for_user(self, user_uid: str) -> List[Swipe]:
        return list(self._swipes)


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1, 12, 0, 0)


def _swipe(swipe_id: str, direction: SwipeDirection) -> Swipe:
    return Swipe(
        id=swipe_id,
        session_id="s1",
        card_data='{"id": "x"}',
        decision=direction,
        created_at=datetime(2030, 1, 1),
    )


@pytest.mark.asyncio
async def test_returns_profile_with_compiled_stats():
    users = FakeUserRepo()
    users.users["u1"] = User(
        id="u1",
        email="a@b.com",
        username="BraveOtter42",
        name="Ada",
        preferred_activities="hikes, concerts",
        created_at=datetime(2025, 5, 5, 9, 0, 0),
    )
    sessions = FakeSessionRepo(
        [
            Session(
                id="s1",
                user_uid="u1",
                location="Austin",
                distance=25.0,
                time_range="tonight",
                created_at=datetime(2030, 1, 1),
            ),
            Session(
                id="s2",
                user_uid="u1",
                location="Dallas",
                distance=10.0,
                time_range="tonight",
                created_at=datetime(2030, 1, 2),
            ),
        ]
    )
    swipes = FakeSwipeRepo(
        [
            _swipe("a", SwipeDirection.LIKE),
            _swipe("b", SwipeDirection.PASS),
            _swipe("c", SwipeDirection.SUPER_LIKE),
        ]
    )
    use_case = GetUserProfile(users, sessions, swipes, FixedClock())

    out = await use_case.execute(GetUserProfileInput(uid="u1"))

    assert out.uid == "u1"
    assert out.username == "BraveOtter42"
    assert out.name == "Ada"
    assert out.preferred_activities == "hikes, concerts"
    assert out.created_at == datetime(2025, 5, 5, 9, 0, 0)
    assert out.stats.sessions == 2
    assert out.stats.swipes == 3
    # LIKE and SUPER_LIKE count as liked; PASS does not.
    assert out.stats.liked_events == 2


@pytest.mark.asyncio
async def test_zero_stats_for_brand_new_user():
    users = FakeUserRepo()
    users.users["u1"] = User(
        id="u1",
        email="a@b.com",
        username="BraveOtter42",
        created_at=datetime(2030, 1, 1),
    )
    use_case = GetUserProfile(
        users, FakeSessionRepo([]), FakeSwipeRepo([]), FixedClock()
    )

    out = await use_case.execute(GetUserProfileInput(uid="u1"))

    assert out.name is None
    assert out.stats.sessions == 0
    assert out.stats.liked_events == 0
    assert out.stats.swipes == 0


@pytest.mark.asyncio
async def test_missing_user_raises_not_found():
    use_case = GetUserProfile(
        FakeUserRepo(), FakeSessionRepo([]), FakeSwipeRepo([]), FixedClock()
    )

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(GetUserProfileInput(uid="ghost"))
