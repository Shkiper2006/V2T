from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TariffCode(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    BUSINESS = "business"


class QueuePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    BUSINESS = "business"


class Tariff(Base):
    __tablename__ = "tariffs"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(64))
    price_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    monthly_messages_quota: Mapped[int] = mapped_column(Integer)
    max_audio_seconds: Mapped[int] = mapped_column(Integer)
    queue_priority: Mapped[str] = mapped_column(String(16), default=QueuePriority.NORMAL.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
