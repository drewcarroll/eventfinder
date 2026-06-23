"""GetEventFeed use case.

Orchestrates discovery, enrichment, persistence, and ranking of events to
produce a personalized swipe feed for a user.

This use case knows WHAT to do, not HOW: it depends only on domain
entities/services and application ports — never on infrastructure.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.application.dtos.event_dtos import (
    GetEventFeedInput,
    GetEventFeedOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.mappers.event_mapper import EventMapper
from src.application.ports.card_normalizer_port import CardNormalizerPort
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import EventDiscoveryPort
from src.application.ports.event_enricher_port import EventEnricherPort
from src.domain.entities.event import Event
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.card_merger import CardMerger
from src.domain.services.recommendation_scorer import RecommendationScorer


def _as_naive_utc(value: datetime | None) -> datetime | None:
    """Normalize an (optionally tz-aware) datetime to naive UTC, matching the
    convention used for stored event start times. Returns ``None`` unchanged."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class GetEventFeed:
    """Produce a ranked, personalized list of events for a user."""

    def __init__(
        self,
        users: UserRepository,
        events: EventRepository,
        swipes: SwipeRepository,
        discovery: EventDiscoveryPort,
        normalizer: CardNormalizerPort,
        enricher: EventEnricherPort,
        merger: CardMerger,
        scorer: RecommendationScorer,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._events = events
        self._swipes = swipes
        self._discovery = discovery
        self._normalizer = normalizer
        self._enricher = enricher
        self._merger = merger
        self._scorer = scorer
        self._clock = clock

    async def execute(self, dto: GetEventFeedInput) -> GetEventFeedOutput:
        user = await self._users.get_by_id(dto.user_id)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_id}' not found")

        # Discover candidate events from an external source (port). Fold the
        # search radius into the query text so the discovery provider can
        # bias toward nearby results.
        discovered = await self._discovery.discover(
            self._search_query(dto), dto.limit
        )

        # Normalize the raw web results into the unified card schema and
        # generate complementary activity cards (LLM-backed port). Both
        # arrive as Event entities with availability_times where known.
        normalized = await self._normalizer.normalize(discovered, user)
        activities = await self._normalizer.generate_activities(
            dto.query, user, dto.limit
        )
        new_cards = normalized + activities

        # Persist the normalized cards so future feeds can reuse them.
        for card in new_cards:
            await self._events.save(card)

        # Enrich with AI-generated, user-tailored copy (port).
        enriched = await self._enricher.enrich(new_cards, user)

        # Merge events and activities with previously stored, unseen cards
        # into one list, deduplicating shared offerings (domain service).
        unseen = await self._events.list_unseen_for_user(
            dto.user_id, dto.limit
        )
        candidates = self._merger.merge(enriched, unseen)

        # Keep only cards that fall in the requested time window.
        candidates = self._within_time_window(candidates, dto)

        # Rank using pure domain logic.
        history = await self._swipes.list_for_user(dto.user_id)
        ranked = self._scorer.rank(
            candidates, user, history, self._clock.now()
        )

        return GetEventFeedOutput(
            events=[EventMapper.to_dto(e) for e in ranked[: dto.limit]]
        )

    @staticmethod
    def _search_query(dto: GetEventFeedInput) -> str:
        """Compose the discovery query, appending the radius when set."""
        if dto.radius_km is not None:
            return f"{dto.query} within {int(dto.radius_km)} km"
        return dto.query

    @staticmethod
    def _within_time_window(
        events: list[Event], dto: GetEventFeedInput
    ) -> list[Event]:
        """Filter events to the requested ``[starts_after, starts_before]``
        window. Bounds default to wide-open when unset, and are normalized to
        naive UTC to match the stored event start times."""
        if dto.starts_after is None and dto.starts_before is None:
            return events
        start = _as_naive_utc(dto.starts_after) or datetime.min
        end = _as_naive_utc(dto.starts_before) or datetime.max
        return [e for e in events if e.starts_within(start, end)]
