"""Integration tests for the SQLAlchemy repositories against real Postgres.

These exercise each repository's save + read methods end-to-end, mapping
domain entities to rows and back. They are the regression guard for schema
drift. Run against a throwaway DB (see conftest); skipped when no Postgres
is available.
"""
from datetime import datetime

from src.domain.entities.event import CARD_TYPE_ACTIVITY, Event
from src.domain.entities.liked_idea import LikedIdea
from src.domain.entities.user import User
from src.domain.value_objects.availability_window import AvailabilityWindow
from src.domain.value_objects.geo_location import GeoLocation
from src.infrastructure.persistence.sql_event_repository import (
    SqlEventRepository,
)
from src.infrastructure.persistence.sql_liked_idea_repository import (
    SqlLikedIdeaRepository,
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


def _liked(
    idea_id: str, *, user_uid: str = "u1", key: str = None
) -> LikedIdea:
    return LikedIdea(
        id=idea_id,
        user_uid=user_uid,
        idea_key=key or idea_id,
        card_data=f'{{"id": "{idea_id}", "title": "Idea {idea_id}"}}',
        created_at=datetime(2030, 1, 1, 12, 0, 0),
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


async def test_liked_idea_roundtrip(repo_session):
    await _seed_user(repo_session)
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("a"))

    ideas = await repo.list_for_user("u1")
    assert len(ideas) == 1
    assert ideas[0].idea_key == "a"
    assert '"title": "Idea a"' in ideas[0].card_data


async def test_liked_ideas_are_listed_newest_first(repo_session):
    await _seed_user(repo_session)
    repo = SqlLikedIdeaRepository(repo_session)
    older = LikedIdea(
        id="old",
        user_uid="u1",
        idea_key="old",
        card_data='{"id": "old"}',
        created_at=datetime(2030, 1, 1),
    )
    newer = LikedIdea(
        id="new",
        user_uid="u1",
        idea_key="new",
        card_data='{"id": "new"}',
        created_at=datetime(2030, 6, 1),
    )
    await repo.save(older)
    await repo.save(newer)

    assert [i.id for i in await repo.list_for_user("u1")] == ["new", "old"]


async def test_re_liking_same_idea_is_idempotent(repo_session):
    await _seed_user(repo_session)
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("first-row", key="farleys"))
    # Same user + idea_key liked again: refreshes, does not duplicate.
    await repo.save(_liked("second-row", key="farleys"))

    ideas = await repo.list_for_user("u1")
    assert len(ideas) == 1
    assert ideas[0].idea_key == "farleys"


async def test_delete_removes_liked_idea_and_reports_hit(repo_session):
    await _seed_user(repo_session)
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("a", key="farleys"))

    removed = await repo.delete("u1", "farleys")

    assert removed is True
    assert await repo.list_for_user("u1") == []


async def test_delete_unknown_idea_reports_miss(repo_session):
    await _seed_user(repo_session)
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("a", key="farleys"))

    removed = await repo.delete("u1", "ghost")

    assert removed is False
    assert len(await repo.list_for_user("u1")) == 1


async def test_delete_is_scoped_per_user(repo_session):
    await _seed_user(repo_session, "u1")
    await _seed_user(repo_session, "u2")
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("shared", user_uid="u1", key="shared"))
    await repo.save(_liked("shared", user_uid="u2", key="shared"))

    # u1 deleting their copy must not touch u2's identically-keyed like.
    assert await repo.delete("u1", "shared") is True
    assert await repo.list_for_user("u1") == []
    assert [i.idea_key for i in await repo.list_for_user("u2")] == ["shared"]


async def test_liked_ideas_are_scoped_per_user(repo_session):
    await _seed_user(repo_session, "u1")
    await _seed_user(repo_session, "u2")
    repo = SqlLikedIdeaRepository(repo_session)
    await repo.save(_liked("a", user_uid="u1"))
    await repo.save(_liked("b", user_uid="u2"))

    assert [i.idea_key for i in await repo.list_for_user("u1")] == ["a"]
    assert [i.idea_key for i in await repo.list_for_user("u2")] == ["b"]
