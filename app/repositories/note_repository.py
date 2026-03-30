from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.models import Note


class NoteRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()

    async def create(self, user_id: int, text: str, duration_seconds: int = 0) -> Note:
        async with self._session_factory() as session:
            note = Note(user_id=user_id, text=text, duration_seconds=duration_seconds)
            session.add(note)
            await session.commit()
            await session.refresh(note)
            return note

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Note]:
        async with self._session_factory() as session:
            stmt = select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc()).limit(limit)
            return list(await session.scalars(stmt))
