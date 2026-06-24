"""SyncUser use case.

Reconciles the local user record with the identity asserted by a verified
Firebase ID token: inserts the user on first login, updates their profile
on subsequent logins. The token verification itself is an infrastructure
concern handled before this use case runs.
"""
from __future__ import annotations

from src.application.dtos.user_dtos import SyncUserInput, SyncUserOutput
from src.application.ports.clock_port import ClockPort
from src.application.ports.username_generator_port import (
    UsernameGeneratorPort,
)
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class SyncUser:
    """Upsert a user from their authenticated identity."""

    def __init__(
        self,
        users: UserRepository,
        clock: ClockPort,
        usernames: UsernameGeneratorPort,
    ) -> None:
        self._users = users
        self._clock = clock
        self._usernames = usernames

    async def execute(self, dto: SyncUserInput) -> SyncUserOutput:
        existing = await self._users.get_by_id(dto.uid)

        if existing is None:
            user = User(
                id=dto.uid,
                email=dto.email,
                display_name=dto.display_name,
                username=self._usernames.generate(),
                created_at=self._clock.now(),
            )
            is_new = True
        else:
            existing.update_profile(dto.email, dto.display_name)
            # Backfill a handle for records predating usernames so every
            # user always has one to show on the profile tab.
            if not existing.username:
                existing.username = self._usernames.generate()
            user = existing
            is_new = False

        await self._users.save(user)

        # On insert created_at is the value we just set; on update it is the
        # original timestamp loaded from storage.
        created_at = user.created_at or self._clock.now()
        return SyncUserOutput(
            uid=user.id,
            email=user.email,
            display_name=user.display_name,
            created_at=created_at,
            is_new=is_new,
            username=user.username,
            preferred_activities=user.preferred_activities,
        )
