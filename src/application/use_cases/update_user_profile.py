"""UpdateUserProfile use case.

Applies the user-editable profile fields (chosen handle + free-text
activity preferences) submitted from the profile tab. The user must
already exist — provisioning is owned by SyncUser.
"""
from __future__ import annotations

from src.application.dtos.user_dtos import (
    UpdateUserProfileInput,
    UserProfileOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.domain.repositories.user_repository import UserRepository


class UpdateUserProfile:
    """Persist edits to a user's handle and activity preferences."""

    def __init__(self, users: UserRepository, clock: ClockPort) -> None:
        self._users = users
        self._clock = clock

    async def execute(self, dto: UpdateUserProfileInput) -> UserProfileOutput:
        user = await self._users.get_by_id(dto.uid)
        if user is None:
            raise ResourceNotFoundError(f"User {dto.uid} not found")

        user.update_preferences(dto.username, dto.preferred_activities)
        await self._users.save(user)

        return UserProfileOutput(
            uid=user.id,
            email=user.email,
            username=user.username,
            preferred_activities=user.preferred_activities,
            created_at=user.created_at or self._clock.now(),
        )
