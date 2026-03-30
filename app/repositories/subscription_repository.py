from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_sessionmaker
from app.models import Tariff, User, VoiceQuotaEvent


class SubscriptionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory or get_sessionmaker()

    async def activate_subscription(self, user_id: int) -> User:
        return await self.activate_tariff(user_id=user_id, tariff_code="pro")

    async def activate_tariff(self, user_id: int, tariff_code: str, billing_cycle_days: int = 30) -> User:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            user.tariff = tariff_code

            is_paid_tariff = tariff_code.lower() != "free"
            user.is_subscribed = is_paid_tariff
            if is_paid_tariff:
                period_days = max(1, billing_cycle_days)
                now = datetime.now(tz=timezone.utc)
                current_expiry = user.subscription_expiry
                if current_expiry and current_expiry.tzinfo is None:
                    current_expiry = current_expiry.replace(tzinfo=timezone.utc)
                base_datetime = current_expiry if current_expiry and current_expiry > now else now
                user.subscription_expiry = base_datetime + timedelta(days=period_days)
            else:
                user.subscription_expiry = None

            await session.commit()
            await session.refresh(user)
            return user

    async def has_active_subscription(self, user_id: int) -> tuple[bool, str | None]:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            return self._validate_subscription(user)

    async def get_user(self, user_id: int) -> User:
        async with self._session_factory() as session:
            return await self._get_or_create_user(session=session, user_id=user_id)

    async def save_google_tokens(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> User:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            user.google_access_token = access_token
            if refresh_token:
                user.google_refresh_token = refresh_token
            user.google_token_expires_at = expires_at
            await session.commit()
            await session.refresh(user)
            return user

    async def set_google_notes_mode(self, user_id: int, mode: str) -> User:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            user.google_notes_mode = mode
            await session.commit()
            await session.refresh(user)
            return user

    async def get_tariff(self, tariff_code: str) -> Tariff | None:
        async with self._session_factory() as session:
            stmt = select(Tariff).where(Tariff.code == tariff_code.lower())
            return await session.scalar(stmt)

    async def get_tariffs(self) -> list[Tariff]:
        async with self._session_factory() as session:
            stmt = select(Tariff).order_by(Tariff.price_rub.asc())
            rows = await session.scalars(stmt)
            return list(rows.all())

    async def can_consume_voice(self, user_id: int, duration_seconds: int) -> tuple[bool, str | None]:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)

            is_active, inactive_reason = self._validate_subscription(user)
            if not is_active:
                return False, inactive_reason

            tariff = await self._get_tariff_or_fallback(session=session, tariff_code=user.tariff)
            self._ensure_usage_month(user)

            if duration_seconds > tariff.max_audio_seconds:
                return (
                    False,
                    f"Лимит тарифа {tariff.title}: максимум {tariff.max_audio_seconds}s для одного сообщения.",
                )

            if user.monthly_messages_used >= tariff.monthly_messages_quota:
                return (
                    False,
                    f"Месячный лимит сообщений исчерпан ({tariff.monthly_messages_quota}).",
                )

            return True, None

    async def consume_voice_quota(self, user_id: int) -> User:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            self._ensure_usage_month(user)
            user.monthly_messages_used += 1
            await session.commit()
            await session.refresh(user)
            return user

    async def consume_voice_quota_once(self, user_id: int, request_id: str) -> bool:
        async with self._session_factory() as session:
            user = await self._get_or_create_user(session=session, user_id=user_id)
            self._ensure_usage_month(user)
            session.add(VoiceQuotaEvent(request_id=request_id, user_id=user.id))
            user.monthly_messages_used += 1
            try:
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False

    async def _get_or_create_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.telegram_id == str(user_id))
        user = await session.scalar(stmt)

        if user is None:
            user = User(telegram_id=str(user_id), tariff="free", is_subscribed=False)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def _get_tariff_or_fallback(self, session: AsyncSession, tariff_code: str) -> Tariff:
        stmt = select(Tariff).where(Tariff.code == tariff_code.lower())
        tariff = await session.scalar(stmt)
        if tariff is None:
            fallback_stmt = select(Tariff).where(Tariff.code == "free")
            fallback = await session.scalar(fallback_stmt)
            if fallback is None:
                raise RuntimeError("Tariff seed is missing in database")
            return fallback
        return tariff

    @staticmethod
    def _ensure_usage_month(user: User) -> None:
        current_month = datetime.utcnow().strftime("%Y-%m")
        if user.usage_month != current_month:
            user.usage_month = current_month
            user.monthly_messages_used = 0

    @staticmethod
    def _validate_subscription(user: User) -> tuple[bool, str | None]:
        if user.tariff.lower() == "free":
            return True, None

        expiry = user.subscription_expiry
        if expiry is None:
            return False, "Подписка неактивна: не задан срок действия."
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(tz=timezone.utc):
            return False, "Подписка истекла. Продлите тариф, чтобы продолжить."
        return True, None
