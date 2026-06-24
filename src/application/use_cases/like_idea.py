"""LikeIdea use case.

Records a single idea the user swiped yes on. Liking happens as the user
swipes — there is no session to close — so each yes is persisted on its own.
Re-liking the same idea is idempotent: the repository collapses it onto the
existing record by (user, idea_key).
"""
from __future__ import annotations

from src.application.dtos.liked_idea_dtos import LikeIdeaInput, LikeIdeaOutput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.domain.entities.liked_idea import LikedIdea
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository
from src.domain.repositories.user_repository import UserRepository


class LikeIdea:
    """Persist one idea a user swiped yes on."""

    def __init__(
        self,
        users: UserRepository,
        liked_ideas: LikedIdeaRepository,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._liked_ideas = liked_ideas
        self._ids = ids
        self._clock = clock

    async def execute(self, dto: LikeIdeaInput) -> LikeIdeaOutput:
        user = await self._users.get_by_id(dto.user_uid)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_uid}' not found")

        idea = LikedIdea(
            id=self._ids.new_id(),
            user_uid=dto.user_uid,
            idea_key=dto.idea_key,
            card_data=dto.card_data,
            created_at=self._clock.now(),
        )
        await self._liked_ideas.save(idea)
        return LikeIdeaOutput(idea_id=idea.id)
