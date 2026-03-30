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

    async def list_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        sort: str = "desc",
    ) -> list[Note]:
        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        offset = (safe_page - 1) * safe_page_size

        async with self._session_factory() as session:
            stmt = select(Note).where(Note.user_id == user_id)
            if sort.lower() == "asc":
                stmt = stmt.order_by(Note.created_at.asc())
            else:
                stmt = stmt.order_by(Note.created_at.desc())
            stmt = stmt.offset(offset).limit(safe_page_size)
            return list(await session.scalars(stmt))
