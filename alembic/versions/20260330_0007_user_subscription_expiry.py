"""add user subscription expiry

Revision ID: 20260330_0007
Revises: 20260330_0006
Create Date: 2026-03-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260330_0007"
down_revision: str | None = "20260330_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_expiry", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "subscription_expiry")
