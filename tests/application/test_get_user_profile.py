"""Unit tests for the GetUserProfile use case.

Pure application-layer tests with in-memory fake repositories — no
database, no HTTP. Verifies the profile is returned with activity stats
compiled from the ideas the user has said yes to.
"""
from datetime import datetime
from typing import List, Optional

import pytest

from src.application.dtos.user_dtos import GetUserProfileInput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.use_cases.get_user_profile import GetUserProfile
from src.domain.entities.liked_idea import LikedIdea
from src.domain.entities.user import User
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository
from src.domain.repositories.user_repository import UserRepository


class FakeUserRepo(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FakeLikedIdeaRepo(LikedIdeaRepository):
    def __init__(self, ideas: List[LikedIdea]) -> None:
        self._ideas = ideas

    async def save(self, idea: LikedIdea) -> None:  # pragma: no cover
        self._ideas.append(idea)

    async def list_for_user(self, user_uid: str) -> List[LikedIdea]:
        return [i for i in self._ideas if i.user_uid == user_uid]

    async def delete(
        self, user_uid: str, idea_key: str
    ) -> bool:  # pragma: no cover
        before = len(self._ideas)
        self._ideas = [
            i
            for i in self._ideas
            if not (i.user_uid == user_uid and i.idea_key == idea_key)
        ]
        return len(self._ideas) < before


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1, 12, 0, 0)


def _liked(idea_id: str, user_uid: str = "u1") -> LikedIdea:
    return LikedIdea(
        id=idea_id,
        user_uid=user_uid,
        idea_key=idea_id,
        card_data='{"id": "%s"}' % idea_id,
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
    liked = FakeLikedIdeaRepo([_liked("a"), _liked("b"), _liked("c")])
    use_case = GetUserProfile(users, liked, FixedClock())

    out = await use_case.execute(GetUserProfileInput(uid="u1"))

    assert out.uid == "u1"
    assert out.username == "BraveOtter42"
    assert out.name == "Ada"
    assert out.preferred_activities == "hikes, concerts"
    assert out.created_at == datetime(2025, 5, 5, 9, 0, 0)
    assert out.stats.liked_ideas == 3


@pytest.mark.asyncio
async def test_zero_stats_for_brand_new_user():
    users = FakeUserRepo()
    users.users["u1"] = User(
        id="u1",
        email="a@b.com",
        username="BraveOtter42",
        created_at=datetime(2030, 1, 1),
    )
    use_case = GetUserProfile(users, FakeLikedIdeaRepo([]), FixedClock())

    out = await use_case.execute(GetUserProfileInput(uid="u1"))

    assert out.name is None
    assert out.stats.liked_ideas == 0


@pytest.mark.asyncio
async def test_missing_user_raises_not_found():
    use_case = GetUserProfile(
        FakeUserRepo(), FakeLikedIdeaRepo([]), FixedClock()
    )

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(GetUserProfileInput(uid="ghost"))
