"""DeleteLikedIdea use case.

Removes an idea the user previously swiped yes on. Deletion is scoped to the
authenticated user and the idea's stable ``idea_key`` so a user can only ever
remove their own likes. Deleting an idea the user hasn't liked is treated as a
not-found rather than a silent no-op.
"""
from __future__ import annotations

from src.application.dtos.liked_idea_dtos import DeleteLikedIdeaInput
from src.application.exceptions import ResourceNotFoundError
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository


class DeleteLikedIdea:
    """Remove one idea a user previously said yes to."""

    def __init__(self, liked_ideas: LikedIdeaRepository) -> None:
        self._liked_ideas = liked_ideas

    async def execute(self, dto: DeleteLikedIdeaInput) -> None:
        removed = await self._liked_ideas.delete(dto.user_uid, dto.idea_key)
        if not removed:
            raise ResourceNotFoundError(
                f"Liked idea '{dto.idea_key}' not found"
            )
