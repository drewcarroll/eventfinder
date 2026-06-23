"""ListSessions use case.

Builds a user's swiping history: each past session with summary info
(filters, timestamps, and how many cards were swiped/liked), most recent
first. Counts are derived from the user's swipes so the client can show a
"liked N of M" badge without re-fetching each session.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from src.application.dtos.session_dtos import (
    ListSessionsInput,
    ListSessionsOutput,
    SessionSummaryOutput,
)
from src.domain.entities.swipe import Swipe
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository


class ListSessions:
    """Return a user's past sessions with summary info, most recent first."""

    def __init__(
        self,
        sessions: SessionRepository,
        swipes: SwipeRepository,
    ) -> None:
        self._sessions = sessions
        self._swipes = swipes

    async def execute(self, dto: ListSessionsInput) -> ListSessionsOutput:
        sessions = await self._sessions.list_for_user(dto.user_uid)

        # Group the user's swipes by session once, rather than querying per
        # session, to compile the per-session counts.
        by_session: Dict[str, List[Swipe]] = defaultdict(list)
        for swipe in await self._swipes.list_for_user(dto.user_uid):
            by_session[swipe.session_id].append(swipe)

        summaries = [
            SessionSummaryOutput(
                session_id=session.id,
                location=session.location,
                distance=session.distance,
                time_range=session.time_range,
                created_at=session.created_at,
                ended_at=session.ended_at,
                swipe_count=len(by_session[session.id]),
                yes_count=sum(
                    1 for s in by_session[session.id] if s.is_interested
                ),
            )
            for session in sessions
        ]
        return ListSessionsOutput(sessions=summaries)
