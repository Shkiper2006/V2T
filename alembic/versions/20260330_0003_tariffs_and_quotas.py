"""tariffs and monthly quotas

Revision ID: 20260330_0003
Revises: 20260330_0002
Create Date: 2026-03-30
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260330_0003"
down_revision: str | None = "20260330_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = datetime.now(UTC)
    op.create_table(
        "tariffs",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("price_rub", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("monthly_messages_quota", sa.Integer(), nullable=False),
        sa.Column("max_audio_seconds", sa.Integer(), nullable=False),
        sa.Column("queue_priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )

    op.bulk_insert(
        sa.table(
            "tariffs",
            sa.column("code", sa.String),
            sa.column("title", sa.String),
            sa.column("price_rub", sa.Numeric),
            sa.column("monthly_messages_quota", sa.Integer),
            sa.column("max_audio_seconds", sa.Integer),
            sa.column("queue_priority", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "code": "free",
                "title": "Free",
                "price_rub": 0,
                "monthly_messages_quota": 10,
                "max_audio_seconds": 30,
                "queue_priority": "low",
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "basic",
                "title": "Basic",
                "price_rub": 299,
                "monthly_messages_quota": 200,
                "max_audio_seconds": 120,
                "queue_priority": "normal",
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "pro",
                "title": "Pro",
                "price_rub": 699,
                "monthly_messages_quota": 1000000,
                "max_audio_seconds": 600,
                "queue_priority": "high",
                "created_at": now,
                "updated_at": now,
            },
            {
                "code": "business",
                "title": "Business",
                "price_rub": 1490,
                "monthly_messages_quota": 1000000,
                "max_audio_seconds": 600,
                "queue_priority": "high",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    op.add_column("users", sa.Column("monthly_messages_used", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("usage_month", sa.String(length=7), nullable=False, server_default="2026-03"))


def downgrade() -> None:
    op.drop_column("users", "usage_month")
    op.drop_column("users", "monthly_messages_used")
    op.drop_table("tariffs")
