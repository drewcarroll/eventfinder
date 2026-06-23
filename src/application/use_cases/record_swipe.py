"""RecordSwipe use case.

Records a single decision within an open session. Swipes can only be added
to a session that exists and has not yet been closed.
"""
from __future__ import annotations

from src.application.dtos.swipe_dtos import RecordSwipeInput, RecordSwipeOutput
from src.application.exceptions import ConflictError, ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.domain.entities.swipe import Swipe
from src.domain.repositories.session_repository import SessionRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.value_objects.swipe_direction import SwipeDirection


class RecordSwipe:
    """Persist a swipe decision within a session."""

    def __init__(
        self,
        sessions: SessionRepository,
        swipes: SwipeRepository,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._sessions = sessions
        self._swipes = swipes
        self._ids = ids
        self._clock = clock

    async def execute(self, dto: RecordSwipeInput) -> RecordSwipeOutput:
        session = await self._sessions.get_by_id(dto.session_id)
        if session is None:
            raise ResourceNotFoundError(
                f"Session '{dto.session_id}' not found"
            )
        if not session.is_active:
            raise ConflictError("Cannot swipe in a session that has ended")

        decision = SwipeDirection.from_str(dto.decision)
        swipe = Swipe(
            id=self._ids.new_id(),
            session_id=dto.session_id,
            card_data=dto.card_data,
            decision=decision,
            created_at=self._clock.now(),
        )
        await self._swipes.save(swipe)

        return RecordSwipeOutput(
            swipe_id=swipe.id, interested=swipe.is_interested
        )
