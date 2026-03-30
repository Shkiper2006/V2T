"""add queue priority to tariffs

Revision ID: 20260330_0005
Revises: 20260330_0004
Create Date: 2026-03-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_0005"
down_revision: str | None = "20260330_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tariffs", sa.Column("queue_priority", sa.String(length=16), nullable=False, server_default="normal"))

    op.execute("UPDATE tariffs SET queue_priority='low' WHERE code='free'")
    op.execute("UPDATE tariffs SET queue_priority='normal' WHERE code='basic'")
    op.execute("UPDATE tariffs SET queue_priority='high' WHERE code='pro'")
    op.execute("UPDATE tariffs SET queue_priority='business' WHERE code='business'")


def downgrade() -> None:
    op.drop_column("tariffs", "queue_priority")
