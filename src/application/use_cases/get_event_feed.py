"""GetEventFeed use case.

Orchestrates discovery, enrichment, persistence, and ranking of events to
produce a personalized swipe feed for a user.

This use case knows WHAT to do, not HOW: it depends only on domain
entities/services and application ports — never on infrastructure.
"""
from __future__ import annotations

from src.application.dtos.event_dtos import (
    GetEventFeedInput,
    GetEventFeedOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.mappers.event_mapper import EventMapper
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import EventDiscoveryPort
from src.application.ports.event_enricher_port import EventEnricherPort
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.recommendation_scorer import RecommendationScorer


class GetEventFeed:
    """Produce a ranked, personalized list of events for a user."""

    def __init__(
        self,
        users: UserRepository,
        events: EventRepository,
        swipes: SwipeRepository,
        discovery: EventDiscoveryPort,
        enricher: EventEnricherPort,
        scorer: RecommendationScorer,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._events = events
        self._swipes = swipes
        self._discovery = discovery
        self._enricher = enricher
        self._scorer = scorer
        self._clock = clock

    async def execute(self, dto: GetEventFeedInput) -> GetEventFeedOutput:
        user = await self._users.get_by_id(dto.user_id)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_id}' not found")

        # Discover candidate events from an external source (port).
        discovered = await self._discovery.discover(dto.query, dto.limit)
        for event in discovered:
            await self._events.save(event)

        # Enrich with AI-generated, user-tailored copy (port).
        enriched = await self._enricher.enrich(discovered, user)

        # Combine with previously stored, unseen events.
        unseen = await self._events.list_unseen_for_user(
            dto.user_id, dto.limit
        )
        candidates = self._dedupe(enriched + unseen)

        # Rank using pure domain logic.
        history = await self._swipes.list_for_user(dto.user_id)
        ranked = self._scorer.rank(
            candidates, user, history, self._clock.now()
        )

        return GetEventFeedOutput(
            events=[EventMapper.to_dto(e) for e in ranked[: dto.limit]]
        )

    @staticmethod
    def _dedupe(events: list) -> list:
        seen: set[str] = set()
        result = []
        for event in events:
            if event.id not in seen:
                seen.add(event.id)
                result.append(event)
        return result
