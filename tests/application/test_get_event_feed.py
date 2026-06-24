"""Use case test for GetEventFeed filtering.

Verifies that the search radius is folded into the discovery query and that
the time-window filter keeps only events starting inside the requested
window. In-memory fakes only — no DB, HTTP, or LLM.
"""
from datetime import datetime, timezone
from typing import List, Optional

import pytest

from src.application.dtos.event_dtos import GetEventFeedInput
from src.application.ports.card_ranker_port import RankingUnavailableError
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import DiscoveryQuery
from src.application.use_cases.get_event_feed import GetEventFeed
from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.card_filter import CardFilter
from src.domain.services.card_merger import CardMerger
from src.domain.services.recommendation_scorer import RecommendationScorer
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation


class FakeUserRepo(UserRepository):
    def __init__(self, users):
        self.users = {u.id: u for u in users}

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)


class FakeEventRepo(EventRepository):
    def __init__(self, events):
        self.events = {e.id: e for e in events}

    async def save(self, event: Event) -> None:
        self.events[event.id] = event

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        return self.events.get(event_id)

    async def list_unseen_for_user(self, user_id, limit) -> List[Event]:
        return list(self.events.values())[:limit]


class FakeSwipeRepo(SwipeRepository):
    def __init__(self):
        self.swipes: List[Swipe] = []

    async def save(self, swipe: Swipe) -> None:
        self.swipes.append(swipe)

    async def list_for_session(self, session_id) -> List[Swipe]:
        return [s for s in self.swipes if s.session_id == session_id]

    async def list_for_user(self, user_uid) -> List[Swipe]:
        return list(self.swipes)


class RecordingDiscovery:
    """Returns no new events but records the query it was asked for."""

    def __init__(self):
        self.last_query: Optional[DiscoveryQuery] = None

    async def discover(self, query: DiscoveryQuery) -> List[Event]:
        self.last_query = query
        return []


class NoopNormalizer:
    """Passes web results through unchanged and generates no activities."""

    async def normalize(self, raw, user):
        return raw

    async def generate_activities(
        self,
        query,
        user,
        limit,
        starts_after=None,
        starts_before=None,
        radius_km=None,
    ):
        return []


class NoopRanker:
    """Returns candidates in the order given — no reordering, no dedup."""

    async def rank(self, cards, user, window=None):
        return list(cards)


class RecordingRanker:
    """Returns candidates unchanged but records what it was asked to rank."""

    def __init__(self):
        self.ranked = None
        self.window = None

    async def rank(self, cards, user, window=None):
        self.ranked = list(cards)
        self.window = window
        return list(cards)


class RaisingRanker:
    """Always signals the LLM ranker is unavailable."""

    async def rank(self, cards, user, window=None):
        raise RankingUnavailableError("unavailable in test")


class FixedClock(ClockPort):
    def now(self) -> datetime:
        return datetime(2030, 1, 1)


def _event(event_id: str, starts_at: datetime) -> Event:
    return Event(
        id=event_id,
        title=f"Event {event_id}",
        description="",
        category="music",
        starts_at=starts_at,
        source_url="https://x.com",
    )


def _build(stored_events, ranker=None):
    user = User(id="u1", email="a@b.com")
    users = FakeUserRepo([user])
    events = FakeEventRepo(stored_events)
    swipes = FakeSwipeRepo()
    discovery = RecordingDiscovery()
    use_case = GetEventFeed(
        users=users,
        events=events,
        swipes=swipes,
        discovery=discovery,
        normalizer=NoopNormalizer(),
        ranker=ranker or NoopRanker(),
        merger=CardMerger(),
        card_filter=CardFilter(),
        scorer=RecommendationScorer(),
        clock=FixedClock(),
    )
    return use_case, discovery


@pytest.mark.asyncio
async def test_discovery_request_carries_query_radius_and_time_range():
    use_case, discovery = _build([])
    await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="live music near Austin",
            radius_km=25,
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )
    request = discovery.last_query
    assert request is not None
    assert request.query == "live music near Austin"
    assert request.radius_km == 25
    assert request.starts_after == datetime(2030, 6, 10)
    assert request.starts_before == datetime(2030, 6, 20)


@pytest.mark.asyncio
async def test_time_window_filters_out_events_outside_window():
    inside = _event("in", datetime(2030, 6, 15, 20, 0))
    too_early = _event("early", datetime(2030, 6, 1, 20, 0))
    too_late = _event("late", datetime(2030, 7, 1, 20, 0))
    use_case, _ = _build([inside, too_early, too_late])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="live music",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    ids = {e.id for e in out.events}
    assert ids == {"in"}


@pytest.mark.asyncio
async def test_tz_aware_bounds_compare_against_naive_starts_at():
    inside = _event("in", datetime(2030, 6, 15, 20, 0))
    use_case, _ = _build([inside])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="live music",
            starts_after=datetime(2030, 6, 10, tzinfo=timezone.utc),
            starts_before=datetime(2030, 6, 20, tzinfo=timezone.utc),
        )
    )

    assert [e.id for e in out.events] == ["in"]


@pytest.mark.asyncio
async def test_no_filters_returns_all_events():
    e1 = _event("a", datetime(2030, 6, 15))
    e2 = _event("b", datetime(2099, 1, 1))
    use_case, _ = _build([e1, e2])

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="live music")
    )

    assert {e.id for e in out.events} == {"a", "b"}


@pytest.mark.asyncio
async def test_cards_beyond_max_distance_are_excluded():
    near = Event(
        id="near",
        title="Near Thing",
        description="",
        category="music",
        starts_at=datetime(2030, 6, 15),
        source_url="https://x.com",
        location=GeoLocation(latitude=30.27, longitude=-97.74),
    )
    far = Event(
        id="far",
        title="Far Thing",
        description="",
        category="music",
        starts_at=datetime(2030, 6, 15),
        source_url="https://x.com",
        location=GeoLocation(latitude=29.76, longitude=-95.37),  # ~235 km
    )
    use_case, _ = _build([near, far])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="music",
            latitude=30.2672,
            longitude=-97.7431,
            radius_km=50,
        )
    )

    by_id = {e.id: e for e in out.events}
    assert set(by_id) == {"near"}
    # Distance is computed from the user's location and surfaced on the card.
    assert by_id["near"].distance_km is not None
    assert by_id["near"].distance_km < 50


@pytest.mark.asyncio
async def test_cards_with_no_availability_in_time_range_are_excluded():
    # starts_at lands inside the window but the only availability window is
    # outside it: excluded, because windowed cards filter on overlap.
    windowed_out = Event(
        id="out",
        title="Out Of Range",
        description="",
        category="music",
        starts_at=datetime(2030, 6, 15),
        source_url="https://x.com",
        availability_times=[
            AvailabilityWindow(
                datetime(2030, 7, 1, 9), datetime(2030, 7, 1, 17)
            )
        ],
    )
    # starts_at is outside the window but an availability window overlaps it:
    # kept, because availability is what matters.
    windowed_in = Event(
        id="in",
        title="In Range",
        description="",
        category="music",
        starts_at=datetime(2030, 1, 1),
        source_url="https://x.com",
        availability_times=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 9), datetime(2030, 6, 15, 17)
            )
        ],
    )
    use_case, _ = _build([windowed_out, windowed_in])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="music",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    assert {e.id for e in out.events} == {"in"}


class StubDiscovery:
    """Returns a single raw web result."""

    async def discover(self, query):
        return [
            Event(
                id="web1",
                title="Live Music",
                description="raw",
                category="music",
                starts_at=datetime(2030, 6, 15),
                source_url="https://x.com",
            )
        ]


class StubNormalizer:
    """Populates availability on web results and emits one activity."""

    async def normalize(self, raw, user):
        for event in raw:
            event.availability_times = [
                AvailabilityWindow(
                    datetime(2030, 6, 15, 18), datetime(2030, 6, 15, 22)
                )
            ]
        return raw

    async def generate_activities(
        self,
        query,
        user,
        limit,
        starts_after=None,
        starts_before=None,
        radius_km=None,
    ):
        return [
            Event(
                id="act",
                title="Pottery Class",
                description="make a mug",
                category="art",
                starts_at=datetime(2030, 6, 16),
                source_url="",
                card_type=CARD_TYPE_ACTIVITY,
            )
        ]


@pytest.mark.asyncio
async def test_events_and_activities_merge_and_deduplicate():
    # A stored card that duplicates the generated activity by title.
    stored_dupe = Event(
        id="stored-pottery",
        title="pottery class",
        description="",
        category="art",
        starts_at=datetime(2030, 6, 16),
        source_url="https://old.example",
    )
    user = User(id="u1", email="a@b.com")
    use_case = GetEventFeed(
        users=FakeUserRepo([user]),
        events=FakeEventRepo([stored_dupe]),
        swipes=FakeSwipeRepo(),
        discovery=StubDiscovery(),
        normalizer=StubNormalizer(),
        ranker=NoopRanker(),
        merger=CardMerger(),
        card_filter=CardFilter(),
        scorer=RecommendationScorer(),
        clock=FixedClock(),
    )

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    by_id = {e.id: e for e in out.events}
    # The web event and the activity merge into one list; the stored
    # duplicate of the activity is removed (the fresh activity wins).
    assert set(by_id) == {"web1", "act"}
    assert by_id["act"].card_type == "activity"
    # availability_times is populated on the normalized web result.
    assert by_id["web1"].availability_times


@pytest.mark.asyncio
async def test_feed_is_capped_at_25_unique_cards():
    stored = [_event(f"e{i}", datetime(2030, 6, 15)) for i in range(30)]
    use_case, _ = _build(stored)

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things", limit=30)
    )

    # 30 candidates in, at most 25 out, all distinct.
    assert len(out.events) == 25
    assert len({e.id for e in out.events}) == 25


@pytest.mark.asyncio
async def test_filter_runs_before_rank():
    inside = _event("in", datetime(2030, 6, 15))
    outside = _event("late", datetime(2030, 7, 15))
    ranker = RecordingRanker()
    use_case, _ = _build([inside, outside], ranker=ranker)

    await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    # The ranker only ever sees candidates that already passed the filter.
    assert {c.id for c in ranker.ranked} == {"in"}
    # The requested window is handed to the ranker as (naive-UTC) context.
    assert ranker.window == (datetime(2030, 6, 10), datetime(2030, 6, 20))


@pytest.mark.asyncio
async def test_feed_order_is_the_rankers_order():
    class ReverseRanker:
        def __init__(self):
            self.input_ids = None

        async def rank(self, cards, user, window=None):
            self.input_ids = [c.id for c in cards]
            return list(reversed(cards))

    ranker = ReverseRanker()
    use_case, _ = _build(
        [_event("a", datetime(2030, 6, 15)), _event("b", datetime(2030, 6, 15))],
        ranker=ranker,
    )

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things", limit=30)
    )

    # The surfaced order is exactly what the ranker returned — nothing in
    # this path (no enricher) reorders behind its back.
    assert [e.id for e in out.events] == list(reversed(ranker.input_ids))


@pytest.mark.asyncio
async def test_ranker_failure_degrades_to_scorer_not_empty():
    stored = [
        _event("a", datetime(2030, 6, 15)),
        _event("b", datetime(2030, 6, 16)),
    ]
    use_case, _ = _build(stored, ranker=RaisingRanker())

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things", limit=30)
    )

    # LLM ranking failed, but the feed falls back to the domain scorer
    # rather than going empty.
    assert {e.id for e in out.events} == {"a", "b"}


def test_use_case_no_longer_takes_a_per_card_enricher():
    import inspect

    params = inspect.signature(GetEventFeed.__init__).parameters
    assert "enricher" not in params
    assert "ranker" in params


@pytest.mark.asyncio
async def test_each_source_caps_at_twenty_independently_of_request_limit():
    class RecordingNormalizer:
        def __init__(self):
            self.activity_limit = None

        async def normalize(self, raw, user):
            return raw

        async def generate_activities(
            self,
            query,
            user,
            limit,
            starts_after=None,
            starts_before=None,
            radius_km=None,
        ):
            self.activity_limit = limit
            return []

    normalizer = RecordingNormalizer()
    user = User(id="u1", email="a@b.com")
    discovery = RecordingDiscovery()
    use_case = GetEventFeed(
        users=FakeUserRepo([user]),
        events=FakeEventRepo([]),
        swipes=FakeSwipeRepo(),
        discovery=discovery,
        normalizer=normalizer,
        ranker=NoopRanker(),
        merger=CardMerger(),
        card_filter=CardFilter(),
        scorer=RecommendationScorer(),
        clock=FixedClock(),
    )

    # Request asks for far more than the per-source cap.
    await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things", limit=100)
    )

    # Both sources are pinned to 20 regardless of the request's limit.
    assert discovery.last_query.limit == 20
    assert normalizer.activity_limit == 20
