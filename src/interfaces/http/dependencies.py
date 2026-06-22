"""FastAPI dependency providers for the HTTP interface.

Controllers depend ONLY on use cases (from the application layer). The
concrete wiring of infrastructure to ports/repositories happens in the
composition root (`main.py`) and is injected into FastAPI's app state.
This module exposes typed accessors so controllers stay thin and never
import infrastructure directly.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Depends, Header, HTTPException, Request, status

from src.application.use_cases.get_event_feed import GetEventFeed
from src.application.use_cases.record_swipe import RecordSwipe

# A factory provided by the composition root that, given an auth token,
# builds request-scoped use cases bound to a DB session/unit of work.
UseCaseFactory = Callable[[str], Awaitable["RequestScope"]]


class RequestScope:
    """Holds request-scoped use cases and the authenticated user id."""

    def __init__(
        self,
        user_id: str,
        get_event_feed: GetEventFeed,
        record_swipe: RecordSwipe,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.user_id = user_id
        self.get_event_feed = get_event_feed
        self.record_swipe = record_swipe
        self.commit = commit


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
