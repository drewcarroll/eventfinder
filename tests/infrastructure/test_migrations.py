"""Migration-chain integration test.

Guards the defect that broke this project's schema management: the alembic
chain could not build the schema from scratch (no migration created
``events``; ``0003`` dropped a ``swipes`` table nothing had created). This
runs the full chain on a throwaway database and asserts ``alembic check``
finds no drift — i.e. migrations and ORM models agree. Skipped when no
Postgres server is reachable.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.infrastructure._dbutil import (
    drop_db,
    pg_reachable_async,
    recreate_db,
    urls,
)

_MIG_DB = "event_swiper_migtest"
_ROOT = Path(__file__).resolve().parents[2]


def _alembic(args: list[str], db_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


async def test_fresh_database_migrates_to_head_and_matches_models():
    test_url, admin_dsn = urls(_MIG_DB)
    if not await pg_reachable_async(admin_dsn):
        pytest.skip("PostgreSQL not reachable; skipping migration test")

    await recreate_db(admin_dsn, _MIG_DB)
    try:
        upgrade = _alembic(["upgrade", "head"], test_url)
        assert upgrade.returncode == 0, (
            f"alembic upgrade head failed:\n{upgrade.stdout}\n{upgrade.stderr}"
        )

        # 'check' exits 0 with this message only when the migrated schema
        # matches the ORM models with no outstanding diff.
        check = _alembic(["check"], test_url)
        combined = check.stdout + check.stderr
        assert check.returncode == 0, f"alembic check failed:\n{combined}"
        assert "No new upgrade operations detected" in combined, combined
    finally:
        await drop_db(admin_dsn, _MIG_DB)
