"""Use case test for GetEventFeed filtering.

Verifies that the search radius is folded into the discovery query and that
the time-window filter keeps only events starting inside the requested
window. In-memory fakes only — no DB, HTTP, or LLM.
"""
from datetime import datetime, timezone
from typing import List, Optional

import pytest

from src.application.dtos.event_dtos import GetEventFeedInput
from src.application.ports.clock_port import ClockPort
from src.application.use_cases.get_event_feed import GetEventFeed
from src.domain.entities.event import Event
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.repositories.event_repository import EventRepository
from src.domain.repositories.swipe_repository import SwipeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.recommendation_scorer import RecommendationScorer


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

    async def list_for_user(self, user_id) -> List[Swipe]:
        return [s for s in self.swipes if s.user_id == user_id]

    async def exists(self, user_id, event_id) -> bool:
        return False


class RecordingDiscovery:
    """Returns no new events but records the query it was asked for."""

    def __init__(self):
        self.last_query: Optional[str] = None

    async def discover(self, query: str, limit: int) -> List[Event]:
        self.last_query = query
        return []


class NoopEnricher:
    async def enrich(self, events, user):
        return events


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


def _build(stored_events):
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
        enricher=NoopEnricher(),
        scorer=RecommendationScorer(),
        clock=FixedClock(),
    )
    return use_case, discovery


@pytest.mark.asyncio
async def test_radius_is_folded_into_discovery_query():
    use_case, discovery = _build([])
    await use_case.execute(
        GetEventFeedInput(
            user_id="u1", query="live music near Austin", radius_km=25
        )
    )
    assert discovery.last_query == "live music near Austin within 25 km"


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
