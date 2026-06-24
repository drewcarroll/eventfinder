"""replace sessions/swipes with a flat liked_ideas table

Revision ID: 0006_liked_ideas
Revises: 0005_add_user_name
Create Date: 2026-06-24

Sessions are gone: the home feed cycles ideas rather than running a
bounded "session", and the profile shows a flat list of the ideas the user
said yes to. This drops the ``swipes`` and ``sessions`` tables and adds
``liked_ideas`` — one row per idea a user liked, deduplicated per user by a
stable ``idea_key`` so re-liking the same idea doesn't pile up.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_liked_ideas"
down_revision = "0005_add_user_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "liked_ideas",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_uid", sa.String(length=128), nullable=False),
        sa.Column("idea_key", sa.String(length=512), nullable=False),
        sa.Column("card_data", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_uid"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_uid", "idea_key", name="uq_user_idea"),
    )

    # Swipes belong to sessions, so drop it first to satisfy the FK. Guard
    # with IF EXISTS so a from-scratch ``upgrade head`` stays robust.
    op.execute("DROP TABLE IF EXISTS swipes")
    op.execute("DROP TABLE IF EXISTS sessions")


def downgrade() -> None:
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
    op.drop_table("liked_ideas")
