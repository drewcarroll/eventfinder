"""Use case tests for GetEventFeed.

Verifies the research → ideas pipeline: the search radius and time window
are folded into the discovery (research) query, the idea generator turns
research into candidate cards, and filtering runs before ranking. In-memory
fakes only — no DB, HTTP, or LLM.
"""
from datetime import datetime, timezone
from typing import List, Optional

import pytest

from src.application.dtos.event_dtos import GetEventFeedInput
from src.application.ports.card_ranker_port import RankingUnavailableError
from src.application.ports.clock_port import ClockPort
from src.application.ports.event_discovery_port import DiscoveryQuery
from src.application.use_cases.get_event_feed import GetEventFeed
from src.domain.entities.event import Event
from src.domain.entities.user import User
from src.domain.repositories.event_repository import EventRepository
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
    def __init__(self):
        self.events = {}

    async def save(self, event: Event) -> None:
        self.events[event.id] = event

    async def get_by_id(self, event_id: str) -> Optional[Event]:
        return self.events.get(event_id)


class RecordingDiscovery:
    """Returns no research but records the query it was asked for."""

    def __init__(self):
        self.last_query: Optional[DiscoveryQuery] = None

    async def discover(self, query: DiscoveryQuery) -> List[Event]:
        self.last_query = query
        return []


class StubIdeaGenerator:
    """Returns a fixed set of generated ideas, recording its inputs."""

    def __init__(self, ideas: List[Event]):
        self._ideas = ideas
        self.limit = None
        self.research = None

    async def generate(
        self,
        query,
        user,
        limit,
        research,
        starts_after=None,
        starts_before=None,
        radius_km=None,
    ):
        self.limit = limit
        self.research = research
        return list(self._ideas)


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


class PassthroughVerifier:
    """Keeps every card, recording the window it was asked about."""

    def __init__(self):
        self.window = None
        self.cards = None

    async def verify(self, cards, window):
        self.window = window
        self.cards = list(cards)
        return list(cards)


class DropByIdVerifier:
    """Prunes cards whose id is in the configured drop-set."""

    def __init__(self, drop_ids):
        self._drop = set(drop_ids)

    async def verify(self, cards, window):
        return [c for c in cards if c.id not in self._drop]


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


def _build(
    ideas, ranker=None, discovery=None, idea_generator=None, verifier=None
):
    user = User(id="u1", email="a@b.com")
    users = FakeUserRepo([user])
    discovery = discovery or RecordingDiscovery()
    generator = idea_generator or StubIdeaGenerator(ideas)
    use_case = GetEventFeed(
        users=users,
        events=FakeEventRepo(),
        discovery=discovery,
        idea_generator=generator,
        ranker=ranker or NoopRanker(),
        verifier=verifier or PassthroughVerifier(),
        merger=CardMerger(),
        card_filter=CardFilter(),
        scorer=RecommendationScorer(),
        clock=FixedClock(),
    )
    return use_case, discovery, generator


@pytest.mark.asyncio
async def test_research_request_carries_query_radius_and_time_range():
    use_case, discovery, _ = _build([])
    await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do near Austin",
            radius_km=25,
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )
    request = discovery.last_query
    assert request is not None
    assert request.query == "things to do near Austin"
    assert request.radius_km == 25
    assert request.starts_after == datetime(2030, 6, 10)
    assert request.starts_before == datetime(2030, 6, 20)


@pytest.mark.asyncio
async def test_research_results_are_passed_to_the_idea_generator():
    research = [_event("web1", datetime(2030, 6, 15))]

    class StubDiscovery:
        async def discover(self, query):
            return list(research)

    use_case, _, generator = _build(
        [_event("idea1", datetime(2030, 6, 15))],
        discovery=StubDiscovery(),
    )
    await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    assert [e.id for e in generator.research] == ["web1"]


@pytest.mark.asyncio
async def test_time_window_filters_out_ideas_outside_window():
    ideas = [
        _event("in", datetime(2030, 6, 15, 20, 0)),
        _event("early", datetime(2030, 6, 1, 20, 0)),
        _event("late", datetime(2030, 7, 1, 20, 0)),
    ]
    use_case, _, _ = _build(ideas)

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    assert {e.id for e in out.events} == {"in"}


@pytest.mark.asyncio
async def test_tz_aware_bounds_compare_against_naive_starts_at():
    use_case, _, _ = _build([_event("in", datetime(2030, 6, 15, 20, 0))])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 10, tzinfo=timezone.utc),
            starts_before=datetime(2030, 6, 20, tzinfo=timezone.utc),
        )
    )

    assert [e.id for e in out.events] == ["in"]


@pytest.mark.asyncio
async def test_no_filters_returns_all_ideas():
    ideas = [
        _event("a", datetime(2030, 6, 15)),
        _event("b", datetime(2099, 1, 1)),
    ]
    use_case, _, _ = _build(ideas)

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
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
    use_case, _, _ = _build([near, far])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            latitude=30.2672,
            longitude=-97.7431,
            radius_km=50,
        )
    )

    by_id = {e.id: e for e in out.events}
    assert set(by_id) == {"near"}
    assert by_id["near"].distance_km is not None
    assert by_id["near"].distance_km < 50


@pytest.mark.asyncio
async def test_cards_with_no_availability_in_time_range_are_excluded():
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
    use_case, _, _ = _build([windowed_out, windowed_in])

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    assert {e.id for e in out.events} == {"in"}


@pytest.mark.asyncio
async def test_generated_ideas_are_deduplicated():
    # Two generated cards describing the same offering (same title).
    dupe_a = Event(
        id="a",
        title="Grab a drink at Farley's",
        description="",
        category="bar",
        starts_at=datetime(2030, 6, 16),
        source_url="",
    )
    dupe_b = Event(
        id="b",
        title="grab a drink at farley's",
        description="",
        category="bar",
        starts_at=datetime(2030, 6, 16),
        source_url="",
    )
    unique = _event("c", datetime(2030, 6, 16))
    use_case, _, _ = _build([dupe_a, dupe_b, unique])

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    # The two same-title cards collapse to one; the distinct card survives.
    assert len(out.events) == 2


@pytest.mark.asyncio
async def test_feed_is_capped_at_50_unique_cards():
    ideas = [_event(f"e{i}", datetime(2030, 6, 15)) for i in range(60)]
    use_case, _, _ = _build(ideas)

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    assert len(out.events) == 50
    assert len({e.id for e in out.events}) == 50


@pytest.mark.asyncio
async def test_idea_generator_is_asked_for_the_feed_size():
    use_case, _, generator = _build([])
    await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do", limit=5)
    )
    # The generator over-produces to the feed size regardless of the
    # request's limit param.
    assert generator.limit == 50


@pytest.mark.asyncio
async def test_filter_runs_before_rank():
    inside = _event("in", datetime(2030, 6, 15))
    outside = _event("late", datetime(2030, 7, 15))
    ranker = RecordingRanker()
    use_case, _, _ = _build([inside, outside], ranker=ranker)

    await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 10),
            starts_before=datetime(2030, 6, 20),
        )
    )

    assert {c.id for c in ranker.ranked} == {"in"}
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
    use_case, _, _ = _build(
        [_event("a", datetime(2030, 6, 15)), _event("b", datetime(2030, 6, 15))],
        ranker=ranker,
    )

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    assert [e.id for e in out.events] == list(reversed(ranker.input_ids))


@pytest.mark.asyncio
async def test_verifier_prunes_cards_before_ranking():
    inside = _event("keep", datetime(2030, 6, 15, 20, 0))
    bad = _event("drop", datetime(2030, 6, 15, 21, 0))
    ranker = RecordingRanker()
    use_case, _, _ = _build(
        [inside, bad],
        ranker=ranker,
        verifier=DropByIdVerifier({"drop"}),
    )

    out = await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 15, 18, 0),
            starts_before=datetime(2030, 6, 16, 4, 0),
        )
    )

    # The verifier's drop happens before ranking, so the dropped card never
    # reaches the ranker and never reaches the feed.
    assert {e.id for e in out.events} == {"keep"}
    assert {c.id for c in ranker.ranked} == {"keep"}


@pytest.mark.asyncio
async def test_verifier_receives_the_naive_utc_window():
    verifier = PassthroughVerifier()
    use_case, _, _ = _build(
        [_event("a", datetime(2030, 6, 15, 20, 0))],
        verifier=verifier,
    )

    await use_case.execute(
        GetEventFeedInput(
            user_id="u1",
            query="things to do",
            starts_after=datetime(2030, 6, 15, 18, 0, tzinfo=timezone.utc),
            starts_before=datetime(2030, 6, 16, 4, 0, tzinfo=timezone.utc),
        )
    )

    # tz-aware bounds are normalized to naive UTC before the verifier sees them.
    assert verifier.window == (
        datetime(2030, 6, 15, 18, 0),
        datetime(2030, 6, 16, 4, 0),
    )


@pytest.mark.asyncio
async def test_ranker_failure_degrades_to_scorer_not_empty():
    ideas = [
        _event("a", datetime(2030, 6, 15)),
        _event("b", datetime(2030, 6, 16)),
    ]
    use_case, _, _ = _build(ideas, ranker=RaisingRanker())

    out = await use_case.execute(
        GetEventFeedInput(user_id="u1", query="things to do")
    )

    assert {e.id for e in out.events} == {"a", "b"}
