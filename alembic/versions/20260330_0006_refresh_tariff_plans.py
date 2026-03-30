"""refresh tariff plans

Revision ID: 20260330_0006
Revises: 20260330_0005
Create Date: 2026-03-30
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260330_0006"
down_revision: str | None = "20260330_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE tariffs
        SET
            title = CASE code
                WHEN 'free' THEN 'Free'
                WHEN 'basic' THEN 'Basic'
                WHEN 'pro' THEN 'Pro'
                WHEN 'business' THEN 'Business'
                ELSE title
            END,
            price_rub = CASE code
                WHEN 'free' THEN 0
                WHEN 'basic' THEN 299
                WHEN 'pro' THEN 699
                WHEN 'business' THEN 1490
                ELSE price_rub
            END,
            monthly_messages_quota = CASE code
                WHEN 'free' THEN 10
                WHEN 'basic' THEN 200
                WHEN 'pro' THEN 1000000
                WHEN 'business' THEN 1000000
                ELSE monthly_messages_quota
            END,
            max_audio_seconds = CASE code
                WHEN 'free' THEN 30
                WHEN 'basic' THEN 120
                WHEN 'pro' THEN 600
                WHEN 'business' THEN 600
                ELSE max_audio_seconds
            END,
            queue_priority = CASE code
                WHEN 'free' THEN 'low'
                WHEN 'basic' THEN 'normal'
                WHEN 'pro' THEN 'high'
                WHEN 'business' THEN 'high'
                ELSE queue_priority
            END
        WHERE code IN ('free', 'basic', 'pro', 'business');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE tariffs
        SET
            price_rub = CASE code
                WHEN 'free' THEN 0
                WHEN 'basic' THEN 490
                WHEN 'pro' THEN 1490
                WHEN 'business' THEN 4990
                ELSE price_rub
            END,
            monthly_messages_quota = CASE code
                WHEN 'free' THEN 20
                WHEN 'basic' THEN 200
                WHEN 'pro' THEN 1000
                WHEN 'business' THEN 5000
                ELSE monthly_messages_quota
            END,
            max_audio_seconds = CASE code
                WHEN 'free' THEN 120
                WHEN 'basic' THEN 300
                WHEN 'pro' THEN 1800
                WHEN 'business' THEN 3600
                ELSE max_audio_seconds
            END,
            queue_priority = CASE code
                WHEN 'free' THEN 'low'
                WHEN 'basic' THEN 'normal'
                WHEN 'pro' THEN 'high'
                WHEN 'business' THEN 'business'
                ELSE queue_priority
            END
        WHERE code IN ('free', 'basic', 'pro', 'business');
        """
    )
