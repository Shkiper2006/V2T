from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()


def _to_async_url(url: str) -> str:
    if "+psycopg://" in url:
        return url.replace("+psycopg://", "+psycopg_async://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_to_async_url(settings.database_url), echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return SessionLocal
