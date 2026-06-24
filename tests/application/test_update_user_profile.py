"""Unit tests for the UpdateUserProfile use case.

Pure application-layer tests with an in-memory fake repository — no
database, no HTTP.
"""
from datetime import datetime
from typing import Optional

import pytest

from src.application.dtos.user_dtos import UpdateUserProfileInput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.use_cases.update_user_profile import UpdateUserProfile
from src.domain.entities.user import User
from src.domain.exceptions import BusinessRuleViolation
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


def _seed(repo: FakeUserRepo) -> None:
    repo.users["u1"] = User(
        id="u1",
        email="a@b.com",
        username="OldHandle",
        created_at=datetime(2025, 5, 5, 9, 0, 0),
    )


@pytest.mark.asyncio
async def test_updates_username_and_activities():
    repo = FakeUserRepo()
    _seed(repo)
    use_case = UpdateUserProfile(repo, FixedClock())

    out = await use_case.execute(
        UpdateUserProfileInput(
            uid="u1",
            username="NewHandle",
            preferred_activities="hikes, concerts, museums",
        )
    )

    assert out.username == "NewHandle"
    assert out.preferred_activities == "hikes, concerts, museums"
    # created_at is preserved from the stored record.
    assert out.created_at == datetime(2025, 5, 5, 9, 0, 0)
    assert repo.users["u1"].preferred_activities == "hikes, concerts, museums"


@pytest.mark.asyncio
async def test_missing_user_raises_not_found():
    repo = FakeUserRepo()
    use_case = UpdateUserProfile(repo, FixedClock())

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(
            UpdateUserProfileInput(
                uid="ghost", username="X", preferred_activities=""
            )
        )


@pytest.mark.asyncio
async def test_blank_username_rejected():
    repo = FakeUserRepo()
    _seed(repo)
    use_case = UpdateUserProfile(repo, FixedClock())

    with pytest.raises(BusinessRuleViolation):
        await use_case.execute(
            UpdateUserProfileInput(
                uid="u1", username="   ", preferred_activities=""
            )
        )
