"""add optional name to users

Revision ID: 0005_add_user_name
Revises: 0004_add_user_profile_fields
Create Date: 2026-06-24

Adds the optional, user-provided ``name`` column. Distinct from the
generated ``username`` handle and from the identity provider's
``display_name`` — it is null until the user types a name in themselves.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_add_user_name"
down_revision = "0004_add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "name")
