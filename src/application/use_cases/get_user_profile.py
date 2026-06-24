"""GetUserProfile use case.

Returns everything the profile screen needs about the authenticated user:
their stored profile plus aggregate activity stats (sessions held, events
liked, swipes made). The user must already exist — provisioning is owned
by SyncUser.
"""
from __future__ import annotations

from src.application.dtos.user_dtos import (
    GetUserProfileInput,
    UserAccountOutput,
    UserStats,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository


class GetUserProfile:
    """Load a user's profile and compile their activity stats."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        swipes: SwipeRepository,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._swipes = swipes
        self._clock = clock

    async def execute(self, dto: GetUserProfileInput) -> UserAccountOutput:
        user = await self._users.get_by_id(dto.uid)
        if user is None:
            raise ResourceNotFoundError(f"User {dto.uid} not found")

        sessions = await self._sessions.list_for_user(dto.uid)
        swipes = await self._swipes.list_for_user(dto.uid)
        stats = UserStats(
            sessions=len(sessions),
            liked_events=sum(1 for s in swipes if s.is_interested),
            swipes=len(swipes),
        )

        return UserAccountOutput(
            uid=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            preferred_activities=user.preferred_activities,
            created_at=user.created_at or self._clock.now(),
            stats=stats,
        )
