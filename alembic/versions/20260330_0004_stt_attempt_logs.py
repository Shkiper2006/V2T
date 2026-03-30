"""add stt attempt logs

Revision ID: 20260330_0004
Revises: 20260330_0003
Create Date: 2026-03-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_0004"
down_revision: str | None = "20260330_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stt_attempt_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("stt_duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("audio_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stt_attempt_logs_user_id"), "stt_attempt_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stt_attempt_logs_user_id"), table_name="stt_attempt_logs")
    op.drop_table("stt_attempt_logs")
