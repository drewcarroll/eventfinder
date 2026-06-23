"""EndSession use case.

Closes a swiping session, marking the run complete. Once closed, the
session and all its swipes are a saved record that no longer accepts swipes.
"""
from __future__ import annotations

from src.application.dtos.session_dtos import EndSessionInput, EndSessionOutput
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository


class EndSession:
    """Close a swiping session."""

    def __init__(
        self,
        sessions: SessionRepository,
        swipes: SwipeRepository,
        clock: ClockPort,
    ) -> None:
        self._sessions = sessions
        self._swipes = swipes
        self._clock = clock

    async def execute(self, dto: EndSessionInput) -> EndSessionOutput:
        session = await self._sessions.get_by_id(dto.session_id)
        if session is None:
            raise ResourceNotFoundError(
                f"Session '{dto.session_id}' not found"
            )

        session.end(self._clock.now())
        await self._sessions.save(session)

        recorded = await self._swipes.list_for_session(session.id)
        assert session.ended_at is not None  # set by end()
        return EndSessionOutput(
            session_id=session.id,
            ended_at=session.ended_at,
            swipe_count=len(recorded),
        )
