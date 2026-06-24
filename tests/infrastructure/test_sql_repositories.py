"""Integration tests for the SQLAlchemy repositories against real Postgres.

These exercise each repository's save + read methods end-to-end, mapping
domain entities to rows and back. They are the regression guard for schema
drift — most directly for ``list_unseen_for_user``, which previously queried
columns (`SwipeModel.event_id`/`user_id`) that don't exist on the
session-scoped swipes schema. Run against a throwaway DB (see conftest);
skipped when no Postgres is available.
"""
from datetime import datetime

from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.session import Session
from src.domain.entities.swipe import Swipe
from src.domain.entities.user import User
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation
from src.domain.value_objects.swipe_direction import SwipeDirection
from src.infrastructure.persistence.sql_event_repository import (
    SqlEventRepository,
)
from src.infrastructure.persistence.sql_session_repository import (
    SqlSessionRepository,
)
from src.infrastructure.persistence.sql_swipe_repository import (
    SqlSwipeRepository,
)
from src.infrastructure.persistence.sql_user_repository import (
    SqlUserRepository,
)


def _user(uid: str = "u1") -> User:
    return User(
        id=uid,
        email=f"{uid}@test.com",
        preferred_categories=["jazz"],
        created_at=datetime(2030, 1, 1),
    )


def _event(event_id: str, *, card_type: str = CARD_TYPE_ACTIVITY) -> Event:
    return Event(
        id=event_id,
        title=f"Event {event_id}",
        description="a thing to do",
        category="music",
        starts_at=datetime(2030, 6, 15, 20, 0),
        source_url="https://x.com",
        location=GeoLocation(30.27, -97.74),
        card_type=card_type,
        availability_times=[
            AvailabilityWindow(
                datetime(2030, 6, 15, 9), datetime(2030, 6, 15, 17)
            )
        ],
    )


async def _seed_user(session, uid: str = "u1") -> User:
    user = _user(uid)
    await SqlUserRepository(session).save(user)
    return user


async def _seed_swipe(session, *, user_uid: str, event_id: str) -> None:
    """Record that ``user_uid`` swiped ``event_id`` (session-scoped swipe)."""
    await SqlSessionRepository(session).save(
        Session(
            id=f"sess-{event_id}",
            user_uid=user_uid,
            location="Austin",
            distance=25.0,
            time_range="next7Days",
            created_at=datetime(2030, 1, 1),
        )
    )
    await SqlSwipeRepository(session).save(
        Swipe(
            id=f"swipe-{event_id}",
            session_id=f"sess-{event_id}",
            card_data=f'{{"id": "{event_id}"}}',
            decision=SwipeDirection.LIKE,
            created_at=datetime(2030, 1, 1),
        )
    )


async def test_user_roundtrip(repo_session):
    repo = SqlUserRepository(repo_session)
    await repo.save(_user("alice"))

    got = await repo.get_by_id("alice")
    assert got is not None
    assert got.email == "alice@test.com"
    assert got.preferred_categories == ["jazz"]


async def test_event_roundtrip_preserves_card_fields(repo_session):
    repo = SqlEventRepository(repo_session)
    await repo.save(_event("e1"))

    got = await repo.get_by_id("e1")
    assert got is not None
    assert got.card_type == CARD_TYPE_ACTIVITY
    assert got.location is not None
    assert len(got.availability_times) == 1
    assert got.availability_times[0].starts_at == datetime(2030, 6, 15, 9)


async def test_session_roundtrip(repo_session):
    await _seed_user(repo_session)
    sessions = SqlSessionRepository(repo_session)
    await sessions.save(
        Session(
            id="s1",
            user_uid="u1",
            location="Austin",
            distance=25.0,
            time_range="next7Days",
            created_at=datetime(2030, 1, 1),
        )
    )

    got = await sessions.get_by_id("s1")
    assert got is not None and got.user_uid == "u1"
    assert [s.id for s in await sessions.list_for_user("u1")] == ["s1"]


async def test_swipe_roundtrip_links_user_via_session(repo_session):
    await _seed_user(repo_session)
    await SqlEventRepository(repo_session).save(_event("e1"))
    await _seed_swipe(repo_session, user_uid="u1", event_id="e1")

    swipes = SqlSwipeRepository(repo_session)
    assert len(await swipes.list_for_session("sess-e1")) == 1
    by_user = await swipes.list_for_user("u1")
    assert len(by_user) == 1
    assert by_user[0].decision == SwipeDirection.LIKE


async def test_list_unseen_excludes_already_swiped_cards(repo_session):
    # The exact regression: a swiped card must be filtered out of "unseen".
    await _seed_user(repo_session)
    events = SqlEventRepository(repo_session)
    await events.save(_event("seen"))
    await events.save(_event("fresh"))
    await _seed_swipe(repo_session, user_uid="u1", event_id="seen")

    unseen = await events.list_unseen_for_user("u1", 25)

    ids = {e.id for e in unseen}
    assert "fresh" in ids
    assert "seen" not in ids


async def test_list_unseen_returns_all_when_no_swipes(repo_session):
    await _seed_user(repo_session)
    events = SqlEventRepository(repo_session)
    await events.save(_event("a"))
    await events.save(_event("b"))

    unseen = await events.list_unseen_for_user("u1", 25)

    assert {e.id for e in unseen} == {"a", "b"}


async def test_list_unseen_respects_limit(repo_session):
    await _seed_user(repo_session)
    events = SqlEventRepository(repo_session)
    for i in range(5):
        await events.save(_event(f"e{i}"))

    assert len(await events.list_unseen_for_user("u1", 3)) == 3
