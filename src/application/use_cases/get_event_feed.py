"""GetEventFeed use case.

Produces a personalized swipe feed via a two-stage pipeline:

1. RESEARCH — discover raw web material about the area (events, venues,
   notable spots) for the given location and time window.
2. IDEAS — turn that research into a large set of concrete, single-idea
   cards (one specific, do-able thing per card), then filter and rank them.

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
from src.application.ports.card_ranker_port import (
    CardRankerPort,
    RankingUnavailableError,
)
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import (
    DiscoveryQuery,
    EventDiscoveryPort,
)
from src.application.ports.idea_generator_port import IdeaGeneratorPort
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.card_filter import CardFilter
from src.domain.services.card_merger import CardMerger
from src.domain.services.recommendation_scorer import RecommendationScorer
from src.domain.value_objects.geo_location import GeoLocation

# Research over-fetches relative to the feed so generation has plenty of raw
# material to ground specific ideas in; the ideas stage then produces a much
# larger, deduplicated deck. The feed size is the final cap on cards served.
_RESEARCH_LIMIT = 20
_FEED_SIZE = 50


def _as_naive_utc(value: datetime | None) -> datetime | None:
    """Normalize an (optionally tz-aware) datetime to naive UTC, matching the
    convention used for stored event start times. ``None`` passes through."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class GetEventFeed:
    """Produce a ranked, personalized list of specific ideas for a user."""

    def __init__(
        self,
        users: UserRepository,
        events: EventRepository,
        discovery: EventDiscoveryPort,
        idea_generator: IdeaGeneratorPort,
        ranker: CardRankerPort,
        merger: CardMerger,
        card_filter: CardFilter,
        scorer: RecommendationScorer,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._events = events
        self._discovery = discovery
        self._idea_generator = idea_generator
        self._ranker = ranker
        self._merger = merger
        self._card_filter = card_filter
        self._scorer = scorer
        self._clock = clock

    async def execute(self, dto: GetEventFeedInput) -> GetEventFeedOutput:
        user = await self._users.get_by_id(dto.user_id)
        if user is None:
            raise ResourceNotFoundError(f"User '{dto.user_id}' not found")

        # The user's location, when supplied, drives distance filtering and
        # the per-card distance annotation.
        origin = (
            GeoLocation(latitude=dto.latitude, longitude=dto.longitude)
            if dto.latitude is not None and dto.longitude is not None
            else None
        )

        # Stage 1 — research the area. The raw web results are source
        # material, not cards: the ideas stage reads them and grounds
        # concrete suggestions in them rather than surfacing scraped,
        # list-shaped pages directly.
        research = await self._discovery.discover(
            DiscoveryQuery(
                query=dto.query,
                limit=_RESEARCH_LIMIT,
                radius_km=dto.radius_km,
                starts_after=dto.starts_after,
                starts_before=dto.starts_before,
            )
        )

        # Stage 2 — turn research into a large deck of specific, single-idea
        # cards tailored to the user and the requested window/radius.
        ideas = await self._idea_generator.generate(
            dto.query,
            user,
            _FEED_SIZE,
            research,
            starts_after=dto.starts_after,
            starts_before=dto.starts_before,
            radius_km=dto.radius_km,
        )

        # Persist generated cards so the rest of the system (e.g. liked-idea
        # snapshots) has a consistent record of what was shown.
        for card in ideas:
            await self._events.save(card)

        # Deduplicate any same-offering cards (domain service).
        candidates = self._merger.merge(ideas)

        # Server-side filtering (domain service) runs BEFORE ranking: drop
        # cards beyond the max distance and cards with no availability inside
        # the requested window. Bounds are naive UTC to match stored times.
        starts_after = _as_naive_utc(dto.starts_after)
        starts_before = _as_naive_utc(dto.starts_before)
        candidates = self._card_filter.filter(
            candidates,
            origin=origin,
            max_distance_km=dto.radius_km,
            starts_after=starts_after,
            starts_before=starts_before,
        )

        # Rank with the LLM ranker; on any failure fall back to deterministic
        # domain scoring so the feed degrades to a sensible order rather than
        # going empty.
        try:
            ranked = await self._ranker.rank(
                candidates, user, (starts_after, starts_before)
            )
        except RankingUnavailableError:
            ranked = self._scorer.rank(candidates, user, self._clock.now())

        return GetEventFeedOutput(
            events=[
                EventMapper.to_dto(e, origin=origin)
                for e in ranked[:_FEED_SIZE]
            ]
        )
