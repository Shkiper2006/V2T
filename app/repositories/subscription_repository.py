from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.models import User


class SubscriptionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()

    async def activate_subscription(self, user_id: int) -> User:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            user.is_subscribed = True
            user.tariff = "pro"
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user(self, user_id: int) -> User:
        async with self._session_factory() as session:
            return await self._get_or_create_user(session=session, user_id=user_id)

    async def _get_or_create_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.telegram_id == str(user_id))
        user = await session.scalar(stmt)

        if user is None:
            user = User(telegram_id=str(user_id), tariff="basic", is_subscribed=False)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user
