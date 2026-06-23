"""GetSessionDetail use case.

Returns one session's full detail — its filters, timestamps, and the
compiled yes list (the cards swiped yes, in swipe order). The lookup is
scoped to the owner: a session that belongs to another user is reported as
not found, so existence never leaks across users.
"""
from __future__ import annotations

from typing import List

from src.application.dtos.session_dtos import (
    GetSessionDetailInput,
    SessionDetailOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository


class GetSessionDetail:
    """Return a single session's full detail for its owner."""

    def __init__(
        self,
        sessions: SessionRepository,
        swipes: SwipeRepository,
    ) -> None:
        self._sessions = sessions
        self._swipes = swipes

    async def execute(self, dto: GetSessionDetailInput) -> SessionDetailOutput:
        session = await self._sessions.get_by_id(dto.session_id)
        # A missing session and one owned by someone else are both "not
        # found" — never reveal that another user's session exists.
        if session is None or session.user_uid != dto.user_uid:
            raise ResourceNotFoundError(
                f"Session '{dto.session_id}' not found"
            )

        decisions = await self._swipes.list_for_session(session.id)
        yes: List[str] = [s.card_data for s in decisions if s.is_interested]

        return SessionDetailOutput(
            session_id=session.id,
            location=session.location,
            distance=session.distance,
            time_range=session.time_range,
            created_at=session.created_at,
            ended_at=session.ended_at,
            swipe_count=len(decisions),
            yes=yes,
        )
