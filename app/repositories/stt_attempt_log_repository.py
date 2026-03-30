from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.models import STTAttemptLog


class STTAttemptLogRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()

    async def create(
        self,
        user_id: int,
        provider: str,
        success: bool,
        retryable: bool,
        stt_duration_seconds: float,
        audio_duration_seconds: int,
        error_code: str | None = None,
        request_timestamp: datetime | None = None,
    ) -> STTAttemptLog:
        async with self._session_factory() as session:
            log = STTAttemptLog(
                user_id=user_id,
                provider=provider,
                success=success,
                retryable=retryable,
                error_code=error_code,
                stt_duration_seconds=stt_duration_seconds,
                audio_duration_seconds=audio_duration_seconds,
                request_timestamp=request_timestamp,
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log
