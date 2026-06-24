"""GetEventFeed use case.

Orchestrates discovery, generation, normalization, filtering, and ranking
of cards to produce a personalized swipe feed for a user.

This use case knows WHAT to do, not HOW: it depends only on domain
entities/services and application ports — never on infrastructure.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.application.dtos.event_dtos import (
    GetEventFeedInput,
    GetEventFeedOutput,
)
from src.application.exceptions import ResourceNotFoundError
from src.application.mappers.event_mapper import EventMapper
from src.application.ports.card_normalizer_port import CardNormalizerPort
from src.application.ports.card_ranker_port import (
    CardRankerPort,
    RankingUnavailableError,
)
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import (
    DiscoveryQuery,
    EventDiscoveryPort,
)
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.card_filter import CardFilter
from src.domain.services.card_merger import CardMerger
from src.domain.services.recommendation_scorer import RecommendationScorer
from src.domain.value_objects.geo_location import GeoLocation

# Per-source candidate caps and the final feed size, decoupled so each can
# be tuned independently: the two sources over-fetch relative to the feed so
# ranking and filtering have a healthy pool to draw from.
_DISCOVERY_LIMIT = 20
_ACTIVITY_LIMIT = 20
_FEED_SIZE = 25


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
        ranker: CardRankerPort,
        merger: CardMerger,
        card_filter: CardFilter,
        scorer: RecommendationScorer,
        clock: ClockPort,
    ) -> None:
        self._users = users
        self._events = events
        self._swipes = swipes
        self._discovery = discovery
        self._normalizer = normalizer
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

        # Discover web results and generate complementary activity cards
        # concurrently — they are independent LLM/HTTP calls. The discovery
        # adapter builds the provider-specific query from the location text,
        # radius, and time range; generation is steered by the same window.
        discovered, activities = await asyncio.gather(
            self._discovery.discover(
                DiscoveryQuery(
                    query=dto.query,
                    limit=_DISCOVERY_LIMIT,
                    radius_km=dto.radius_km,
                    starts_after=dto.starts_after,
                    starts_before=dto.starts_before,
                )
            ),
            self._normalizer.generate_activities(
                dto.query,
                user,
                _ACTIVITY_LIMIT,
                starts_after=dto.starts_after,
                starts_before=dto.starts_before,
                radius_km=dto.radius_km,
            ),
        )

        # Normalize only the raw web results into the unified card schema
        # (this also rewrites their descriptions, so no per-card enricher is
        # needed here). Generated activities already arrive normalized.
        normalized = await self._normalizer.normalize(discovered, user)
        new_cards = normalized + activities

        # Persist the new cards so future feeds can reuse them.
        for card in new_cards:
            await self._events.save(card)

        # Merge events and activities with previously stored, unseen cards
        # into one list, deduplicating shared offerings (domain service).
        unseen = await self._events.list_unseen_for_user(
            dto.user_id, _FEED_SIZE
        )
        candidates = self._merger.merge(new_cards, unseen)

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
            history = await self._swipes.list_for_user(dto.user_id)
            ranked = self._scorer.rank(
                candidates, user, history, self._clock.now()
            )

        return GetEventFeedOutput(
            events=[
                EventMapper.to_dto(e, origin=origin)
                for e in ranked[:_FEED_SIZE]
            ]
        )
