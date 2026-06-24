"""ListLikedIdeas use case.

Returns the ideas a user said yes to, most recently liked first — the flat
list shown on the profile now that swiping runs aren't grouped into
sessions.
"""
from __future__ import annotations

from src.application.dtos.liked_idea_dtos import (
    ListLikedIdeasInput,
    ListLikedIdeasOutput,
)
from src.domain.repositories.liked_idea_repository import LikedIdeaRepository


class ListLikedIdeas:
    """Return a user's liked ideas, newest first."""

    def __init__(self, liked_ideas: LikedIdeaRepository) -> None:
        self._liked_ideas = liked_ideas

    async def execute(
        self, dto: ListLikedIdeasInput
    ) -> ListLikedIdeasOutput:
        ideas = await self._liked_ideas.list_for_user(dto.user_uid)
        return ListLikedIdeasOutput(ideas=[idea.card_data for idea in ideas])
