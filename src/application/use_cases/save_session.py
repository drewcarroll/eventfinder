"""SaveSession use case.

Persists a completed swiping run in one shot: the session (user + filters)
and every swipe decision made during it. Returns the compiled yes list —
the cards the user swiped yes — so the client can show what they matched.
"""
from __future__ import annotations

from typing import List

from src.application.dtos.session_dtos import (
    SaveSessionInput,
    SaveSessionOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.domain.entities.session import Session
from src.domain.entities.swipe import Swipe
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.value_objects.swipe_direction import SwipeDirection


class SaveSession:
    """Persist a finished session and return the cards swiped yes."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        swipes: SwipeRepository,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._swipes = swipes
        self._ids = ids
        self._clock = clock

    async def execute(self, dto: SaveSessionInput) -> SaveSessionOutput:
        user = await self._users.get_by_id(dto.user_uid)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_uid}' not found")

        # A saved session is a completed run: it opens and closes now.
        now = self._clock.now()
        session = Session(
            id=self._ids.new_id(),
            user_uid=dto.user_uid,
            location=dto.location,
            distance=dto.distance,
            time_range=dto.time_range,
            created_at=now,
            ended_at=now,
        )
        await self._sessions.save(session)

        yes: List[str] = []
        for decision in dto.swipes:
            swipe = Swipe(
                id=self._ids.new_id(),
                session_id=session.id,
                card_data=decision.card_data,
                decision=SwipeDirection.from_str(decision.decision),
                created_at=now,
            )
            await self._swipes.save(swipe)
            if swipe.is_interested:
                yes.append(swipe.card_data)

        return SaveSessionOutput(session_id=session.id, yes=yes)
