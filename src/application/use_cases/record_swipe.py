"""RecordSwipe use case.

Records a user's decision on an event, enforcing the one-swipe-per-event
business rule and updating user preference signals.
"""
from __future__ import annotations

from src.application.dtos.swipe_dtos import RecordSwipeInput, RecordSwipeOutput
from src.application.exceptions import ConflictError, ResourceNotFoundError
from src.application.ports.clock_port import ClockPort
from src.application.ports.id_generator_port import IdGeneratorPort
from src.domain.entities.swipe import Swipe
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.value_objects.swipe_direction import SwipeDirection


class RecordSwipe:
    """Persist a swipe decision for a user/event pair."""

    def __init__(
        self,
        users: UserRepository,
        events: EventRepository,
        swipes: SwipeRepository,
        ids: IdGeneratorPort,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._events = events
        self._swipes = swipes
        self._ids = ids
        self._clock = clock

    async def execute(self, dto: RecordSwipeInput) -> RecordSwipeOutput:
        user = await self._users.get_by_id(dto.user_id)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_id}' not found")

        event = await self._events.get_by_id(dto.event_id)
        if event is None:
            raise ResourceNotFoundError(f"Event '{dto.event_id}' not found")

        if await self._swipes.exists(dto.user_id, dto.event_id):
            raise ConflictError("User has already swiped on this event")

        direction = SwipeDirection.from_str(dto.direction)
        swipe = Swipe(
            id=self._ids.new_id(),
            user_id=dto.user_id,
            event_id=dto.event_id,
            direction=direction,
            created_at=self._clock.now(),
        )
        await self._swipes.save(swipe)

        # Update the user's learned preferences from a positive signal.
        if swipe.is_interested:
            user.add_preferred_category(event.category)
            await self._users.save(user)

        return RecordSwipeOutput(
            swipe_id=swipe.id, interested=swipe.is_interested
        )
