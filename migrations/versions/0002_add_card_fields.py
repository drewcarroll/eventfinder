"""add card_type and availability_times to events

Revision ID: 0002_add_card_fields
Revises: 0001a_create_events_table
Create Date: 2026-06-23

Extends the events table to back the unified card schema: ``card_type``
distinguishes web events from generated activities, and
``availability_times`` stores a JSON-encoded list of {starts_at, ends_at}
windows describing when a card can be attended.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_card_fields"
down_revision = "0001a_create_events_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "card_type",
            sa.String(length=32),
            nullable=False,
            server_default="event",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "availability_times",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "availability_times")
    op.drop_column("events", "card_type")
