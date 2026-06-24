"""Liked-ideas HTTP controller.

Records the ideas a user swipes yes on and serves the flat list back for
the profile. Likes are saved as the user swipes — there is no session to
close. Thin adapter: validate input, call the use case, serialize output.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.liked_idea_dtos import (
    LikeIdeaInput,
    ListLikedIdeasInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.liked_idea_schemas import (
    LikedIdeasResponse,
    LikeIdeaRequest,
    LikeIdeaResponse,
)

router = APIRouter(prefix="/api/v1/likes", tags=["likes"])


@router.post(
    "",
    response_model=LikeIdeaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def like_idea(
    body: LikeIdeaRequest,
    scope: RequestScope = ScopeDep,
) -> LikeIdeaResponse:
    """Record one idea the authenticated user swiped yes on."""
    # Identify the idea by its explicit key, the card's id, or — as a last
    # resort — its title, so re-liking the same idea stays idempotent.
    idea_key = (
        body.idea_key
        or _as_str(body.card_data.get("id"))
        or _as_str(body.card_data.get("title"))
    )
    if not idea_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="card_data needs an id or title to identify the idea",
        )

    try:
        result = await scope.like_idea.execute(
            LikeIdeaInput(
                user_uid=scope.user_id,
                idea_key=idea_key,
                card_data=json.dumps(body.card_data),
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return LikeIdeaResponse(idea_id=result.idea_id)


@router.get("", response_model=LikedIdeasResponse)
async def list_liked_ideas(
    scope: RequestScope = ScopeDep,
) -> LikedIdeasResponse:
    """List the authenticated user's liked ideas, most recent first."""
    result = await scope.list_liked_ideas.execute(
        ListLikedIdeasInput(user_uid=scope.user_id)
    )
    return LikedIdeasResponse(
        ideas=[json.loads(card) for card in result.ideas]
    )


def _as_str(value: object) -> str:
    """Coerce a card field to a trimmed string, or '' when unusable."""
    return value.strip() if isinstance(value, str) else ""
