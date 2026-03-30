import logging
import socket
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base, QueuePriority, Tariff

settings = get_settings()
logger = logging.getLogger(__name__)


def _to_async_url(url: str) -> str:
    if "+psycopg://" in url:
        return url.replace("+psycopg://", "+psycopg_async://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _resolve_runtime_database_url(database_url: str) -> str:
    """
    Resolve DB URL for mixed local/docker runs.

    If DATABASE_URL points to non-local host but DNS lookup fails in the
    current runtime, fallback to `localhost`.
    """
    parsed = urlparse(database_url)
    hostname = parsed.hostname
    if hostname in {None, "localhost", "127.0.0.1"}:
        return database_url

    try:
        socket.getaddrinfo(hostname, parsed.port or 5432)
        return database_url
    except socket.gaierror:
        netloc = parsed.netloc.replace(hostname, "localhost", 1)
        fallback_url = urlunparse(parsed._replace(netloc=netloc))
        logger.warning(
            "DATABASE_URL host is unreachable in current environment. "
            "Fallback to localhost is applied.",
            extra={
                "original_database_url": database_url,
                "unreachable_host": hostname,
                "fallback_database_url": fallback_url,
            },
        )
        return fallback_url


runtime_database_url = _resolve_runtime_database_url(settings.database_url)

engine = create_async_engine(_to_async_url(runtime_database_url), echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return SessionLocal


async def init_database() -> None:
    """
    Ensure required tables exist and minimal seed data is present.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        has_tariff = await session.scalar(select(Tariff.code).limit(1))
        if has_tariff is not None:
            return

        now = datetime.utcnow()
        session.add_all(
            [
                Tariff(
                    code="free",
                    title="Free",
                    price_rub=Decimal("0"),
                    monthly_messages_quota=10,
                    max_audio_seconds=30,
                    queue_priority=QueuePriority.LOW.value,
                    created_at=now,
                    updated_at=now,
                ),
                Tariff(
                    code="basic",
                    title="Basic",
                    price_rub=Decimal("299"),
                    monthly_messages_quota=200,
                    max_audio_seconds=120,
                    queue_priority=QueuePriority.NORMAL.value,
                    created_at=now,
                    updated_at=now,
                ),
                Tariff(
                    code="pro",
                    title="Pro",
                    price_rub=Decimal("699"),
                    monthly_messages_quota=1000000,
                    max_audio_seconds=600,
                    queue_priority=QueuePriority.HIGH.value,
                    created_at=now,
                    updated_at=now,
                ),
                Tariff(
                    code="business",
                    title="Business",
                    price_rub=Decimal("1490"),
                    monthly_messages_quota=1000000,
                    max_audio_seconds=600,
                    queue_priority=QueuePriority.HIGH.value,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        await session.commit()
