"""GetUserProfile use case.

Returns everything the profile screen needs about the authenticated user:
their stored profile plus aggregate activity stats (how many ideas they've
said yes to). The user must already exist — provisioning is owned by
SyncUser.
"""
from __future__ import annotations

from src.application.dtos.user_dtos import (
    GetUserProfileInput,
    UserAccountOutput,
    UserStats,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository
from src.domain.repositories.user_repository import UserRepository


class GetUserProfile:
    """Load a user's profile and compile their activity stats."""

    def __init__(
        self,
        users: UserRepository,
        liked_ideas: LikedIdeaRepository,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._liked_ideas = liked_ideas
        self._clock = clock

    async def execute(self, dto: GetUserProfileInput) -> UserAccountOutput:
        user = await self._users.get_by_id(dto.uid)
        if user is None:
            raise ResourceNotFoundError(f"User {dto.uid} not found")

        liked = await self._liked_ideas.list_for_user(dto.uid)
        stats = UserStats(liked_ideas=len(liked))

        return UserAccountOutput(
            uid=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            preferred_activities=user.preferred_activities,
            created_at=user.created_at or self._clock.now(),
            stats=stats,
        )
