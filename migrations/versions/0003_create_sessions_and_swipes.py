"""create sessions table and make swipes session-scoped

Revision ID: 0003_create_sessions_and_swipes
Revises: 0002_add_card_fields
Create Date: 2026-06-23

Introduces the ``sessions`` table — one row per swiping run, capturing the
user, the filters the feed was built from, and the run's open/close times —
and reshapes ``swipes`` to belong to a session. A swipe now stores an opaque
``card_data`` snapshot and a ``decision`` instead of a foreign key to an
event, so a session is a self-contained, saved record of one run.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_create_sessions_and_swipes"
down_revision = "0002_add_card_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_uid", sa.String(length=128), nullable=False),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("time_range", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_uid"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Replace the prior user/event-scoped swipes table with the
    # session-scoped shape. Swipe rows do not survive the redesign. The
    # legacy table only ever existed via ``create_all``, so guard the drop
    # with IF EXISTS to keep a from-scratch ``upgrade head`` working.
    op.execute("DROP TABLE IF EXISTS swipes")
    op.create_table(
        "swipes",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("card_data", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("swipes")
    op.create_table(
        "swipes",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_id", name="uq_user_event_swipe"),
    )
    op.drop_table("sessions")
