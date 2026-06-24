"""Unit tests for the SyncUser use case.

Pure application-layer tests with an in-memory fake repository and a fixed
clock — no database, no Firebase, no HTTP.
"""
from datetime import datetime
from typing import Optional

import pytest

from src.application.dtos.user_dtos import SyncUserInput
from src.application.ports.clock_port import ClockPort
from src.application.ports.username_generator_port import (
    UsernameGeneratorPort,
)
from src.application.use_cases.sync_user import SyncUser
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class FakeUserRepo(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1, 12, 0, 0)


class FixedUsernames(UsernameGeneratorPort):
    def generate(self) -> str:
        return "BraveOtter42"


@pytest.mark.asyncio
async def test_first_login_inserts_new_user():
    repo = FakeUserRepo()
    use_case = SyncUser(repo, FixedClock(), FixedUsernames())

    out = await use_case.execute(
        SyncUserInput(uid="u1", email="a@b.com", display_name="Ada")
    )

    assert out.is_new is True
    assert out.uid == "u1"
    assert out.email == "a@b.com"
    assert out.display_name == "Ada"
    assert out.created_at == datetime(2030, 1, 1, 12, 0, 0)
    # A new user is given a generated handle, independent of identity fields.
    assert out.username == "BraveOtter42"
    assert out.preferred_activities == ""
    assert "u1" in repo.users


@pytest.mark.asyncio
async def test_returning_login_updates_profile_and_preserves_created_at():
    repo = FakeUserRepo()
    repo.users["u1"] = User(
        id="u1",
        email="old@b.com",
        display_name="Old Name",
        username="ChosenHandle",
        preferred_activities="hiking",
        created_at=datetime(2025, 5, 5, 9, 0, 0),
    )
    use_case = SyncUser(repo, FixedClock(), FixedUsernames())

    out = await use_case.execute(
        SyncUserInput(uid="u1", email="new@b.com", display_name="New Name")
    )

    assert out.is_new is False
    assert out.email == "new@b.com"
    assert out.display_name == "New Name"
    # created_at must be preserved from the original record.
    assert out.created_at == datetime(2025, 5, 5, 9, 0, 0)
    # The user's chosen handle and activities survive a re-sync untouched.
    assert out.username == "ChosenHandle"
    assert out.preferred_activities == "hiking"
    assert repo.users["u1"].email == "new@b.com"


@pytest.mark.asyncio
async def test_returning_login_backfills_missing_username():
    repo = FakeUserRepo()
    repo.users["u1"] = User(
        id="u1",
        email="old@b.com",
        created_at=datetime(2025, 5, 5, 9, 0, 0),
    )
    use_case = SyncUser(repo, FixedClock(), FixedUsernames())

    out = await use_case.execute(
        SyncUserInput(uid="u1", email="old@b.com")
    )

    assert out.username == "BraveOtter42"
