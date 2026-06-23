"""StartSession use case.

Opens a swiping session for a user, capturing the filters the feed was
built from. The returned session id scopes every swipe made during the run.
"""
from __future__ import annotations

from src.application.dtos.session_dtos import (
    StartSessionInput,
    StartSessionOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.domain.entities.session import Session
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.user_repository import UserRepository


class StartSession:
    """Open a new swiping session for a user."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._ids = ids
        self._clock = clock

    async def execute(self, dto: StartSessionInput) -> StartSessionOutput:
        user = await self._users.get_by_id(dto.user_uid)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_uid}' not found")

        session = Session(
            id=self._ids.new_id(),
            user_uid=dto.user_uid,
            location=dto.location,
            distance=dto.distance,
            time_range=dto.time_range,
            created_at=self._clock.now(),
        )
        await self._sessions.save(session)
        return StartSessionOutput(session_id=session.id)
