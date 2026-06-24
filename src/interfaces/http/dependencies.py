"""FastAPI dependency providers for the HTTP interface.

Controllers depend ONLY on use cases (from the application layer). The
concrete wiring of infrastructure to ports/repositories happens in the
composition root (`main.py`) and is injected into FastAPI's app state.
This module exposes typed accessors so controllers stay thin and never
import infrastructure directly.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from src.application.use_cases.delete_liked_idea import DeleteLikedIdea
from src.application.use_cases.get_event_feed import GetEventFeed
from src.application.use_cases.get_user_profile import GetUserProfile
from src.application.use_cases.like_idea import LikeIdea
from src.application.use_cases.list_liked_ideas import ListLikedIdeas
from src.application.use_cases.resolve_location import ResolveLocation
from src.application.use_cases.search_locations import SearchLocations
from src.application.use_cases.sync_user import SyncUser
from src.application.use_cases.update_user_profile import UpdateUserProfile

# A factory provided by the composition root that, given an auth token,
# builds request-scoped use cases bound to a DB session/unit of work.
UseCaseFactory = Callable[[str], Awaitable["RequestScope"]]


class RequestScope:
    """Holds request-scoped use cases and the authenticated identity."""

    def __init__(
        self,
        user_id: str,
        get_event_feed: GetEventFeed,
        like_idea: LikeIdea,
        list_liked_ideas: ListLikedIdeas,
        delete_liked_idea: DeleteLikedIdea,
        sync_user: SyncUser,
        resolve_location: ResolveLocation,
        search_locations: SearchLocations,
        commit: Callable[[], Awaitable[None]],
        update_user_profile: Optional[UpdateUserProfile] = None,
        get_user_profile: Optional[GetUserProfile] = None,
        email: str = "",
        display_name: Optional[str] = None,
    ) -> None:
        self.user_id = user_id
        self.get_event_feed = get_event_feed
        self.like_idea = like_idea
        self.list_liked_ideas = list_liked_ideas
        self.delete_liked_idea = delete_liked_idea
        self.sync_user = sync_user
        self.update_user_profile = update_user_profile
        self.get_user_profile = get_user_profile
        self.resolve_location = resolve_location
        self.search_locations = search_locations
        self.commit = commit
        # Profile claims from the verified token, used by /users/sync.
        self.email = email
        self.display_name = display_name


async def get_scope(
    request: Request,
    authorization: str = Header(default=""),
) -> RequestScope:
    """Authenticate the request and build a request scope of use cases."""
    token = _extract_bearer(authorization)
    factory: UseCaseFactory = request.app.state.use_case_factory
    try:
        return await factory(token)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


def _extract_bearer(authorization: str) -> str:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    return authorization.split(" ", 1)[1].strip()


ScopeDep = Depends(get_scope)
