import logging
import socket
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

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
