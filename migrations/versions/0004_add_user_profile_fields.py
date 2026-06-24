"""add username and preferred_activities to users

Revision ID: 0004_add_user_profile_fields
Revises: 0003_create_sessions_and_swipes
Create Date: 2026-06-24

Adds the app-generated, user-editable ``username`` handle and the
free-text ``preferred_activities`` blurb that steers card ranking. Both
back the profile tab. Existing rows are backfilled with a stable
``user_<id-prefix>`` handle; the app replaces empty handles with a random
one on the next login (see SyncUser).
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_add_user_profile_fields"
down_revision = "0003_create_sessions_and_swipes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "username",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "preferred_activities",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    # Backfill a non-empty handle for pre-existing users.
    op.execute(
        "UPDATE users SET username = 'user_' || substr(id, 1, 8) "
        "WHERE username = ''"
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_activities")
    op.drop_column("users", "username")
