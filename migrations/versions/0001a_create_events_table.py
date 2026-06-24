"""create events table

Revision ID: 0001a_create_events_table
Revises: 0001_create_users_table
Create Date: 2026-06-24

Creates the ``events`` table backing the unified card feed in its base
shape. The card-schema columns (``card_type``, ``availability_times``) are
added on top by ``0002_add_card_fields``. This migration exists so the
schema can be built entirely from the alembic chain — previously the table
was only ever created by ``init_db()``'s ``create_all`` at app startup,
which left ``alembic upgrade head`` unable to run on a fresh database.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001a_create_events_table"
down_revision = "0001_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("events")
