"""Helpers for PostgreSQL-backed integration tests.

These create/drop throwaway databases on the same server the app uses
(derived from settings), so repository and migration tests run against real
Postgres. Everything is guarded by :func:`pg_reachable` so the suite skips
gracefully where no database is available (e.g. CI without a DB service).
"""
from __future__ import annotations

import asyncio
from typing import Tuple

import asyncpg

from src.infrastructure.config.settings import get_settings


def urls(db_name: str) -> Tuple[str, str]:
    """Return ``(sqlalchemy_async_url, asyncpg_admin_dsn)`` for ``db_name``.

    The async URL targets the named test database; the admin DSN targets the
    server's default ``postgres`` database for CREATE/DROP DATABASE.
    """
    base = get_settings().database_url  # postgresql+asyncpg://u:p@host:port/db
    prefix, _ = base.rsplit("/", 1)
    test_url = f"{prefix}/{db_name}"
    admin_dsn = f"{prefix}/postgres".replace("+asyncpg", "")
    return test_url, admin_dsn


async def pg_reachable_async(admin_dsn: str) -> bool:
    """Whether the Postgres server accepts a connection within a short window."""
    try:
        conn = await asyncio.wait_for(asyncpg.connect(admin_dsn), timeout=3)
    except Exception:
        return False
    await conn.close()
    return True


def pg_reachable(admin_dsn: str) -> bool:
    """Sync wrapper of :func:`pg_reachable_async` for non-async callers
    (e.g. session-scoped fixtures). Must not run inside a live event loop."""
    return asyncio.run(pg_reachable_async(admin_dsn))


async def recreate_db(admin_dsn: str, db_name: str) -> None:
    """Drop (if present) and create ``db_name``, terminating stray sessions."""
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def drop_db(admin_dsn: str, db_name: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        await conn.close()
