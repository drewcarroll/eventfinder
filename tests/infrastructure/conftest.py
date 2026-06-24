"""Fixtures for PostgreSQL-backed repository tests.

A single throwaway ``event_swiper_test`` database is created once per session
with the schema built from the ORM metadata; each test gets a session wrapped
in a transaction that is rolled back, so tests stay isolated and leave no data
behind. Skips when no Postgres server is reachable.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.infrastructure.persistence.database import Base
import src.infrastructure.persistence.models  # noqa: F401 - register tables

from tests.infrastructure._dbutil import (
    drop_db,
    pg_reachable,
    recreate_db,
    urls,
)

_TEST_DB = "event_swiper_test"


async def _build_schema(test_url: str) -> None:
    engine = create_async_engine(test_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Create the test database + schema once per session; drop it after."""
    test_url, admin_dsn = urls(_TEST_DB)
    if not pg_reachable(admin_dsn):
        pytest.skip("PostgreSQL not reachable; skipping DB integration tests")
    asyncio.run(recreate_db(admin_dsn, _TEST_DB))
    asyncio.run(_build_schema(test_url))
    yield test_url
    asyncio.run(drop_db(admin_dsn, _TEST_DB))


@pytest_asyncio.fixture
async def repo_session(test_db_url: str) -> AsyncSession:
    """A session bound to a transaction that is rolled back after the test."""
    engine = create_async_engine(test_db_url)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
