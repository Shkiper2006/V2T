from app.repositories.subscription_repository import SubscriptionRepository


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    async def subscribe(self, user_id: int) -> str:
        await self.repository.activate_subscription(user_id=user_id)
        return "Подписка Pro активирована ✅"

    async def tariffs(self) -> str:
        tariffs = await self.repository.get_tariffs()
        if not tariffs:
            return "Тарифы пока недоступны."
        lines = ["Тарифы:"]
        for tariff in tariffs:
            lines.append(
                f"- {tariff.title}: {tariff.price_rub}₽/мес, "
                f"{tariff.monthly_messages_quota} сообщений, до {tariff.max_audio_seconds}s аудио"
            )
        return "\n".join(lines)

    async def tariffs_catalog(self) -> list[dict[str, str | int]]:
        tariffs = await self.repository.get_tariffs()
        return [
            {
                "code": tariff.code,
                "title": tariff.title,
                "price": tariff.price_rub,
                "quota": tariff.monthly_messages_quota,
                "max_audio": tariff.max_audio_seconds,
            }
            for tariff in tariffs
        ]

    async def user_tariff(self, user_id: int) -> str:
        user = await self.repository.get_user(user_id)
        return user.tariff

    async def quota_status(self, user_id: int) -> dict[str, int]:
        user = await self.repository.get_user(user_id)
        tariff = await self.repository.get_tariff(user.tariff)
        if tariff is None:
            tariff = await self.repository.get_tariff("free")
        if tariff is None:
            raise RuntimeError("Tariff seed is missing in database")

        used = user.monthly_messages_used
        quota = tariff.monthly_messages_quota
        return {"used": used, "quota": quota, "remaining": max(0, quota - used)}

    async def is_google_connected(self, user_id: int) -> bool:
        user = await self.repository.get_user(user_id)
        return bool(user.google_access_token)

    async def check_voice_allowed(self, user_id: int, duration_seconds: int) -> tuple[bool, str | None]:
        return await self.repository.can_consume_voice(user_id=user_id, duration_seconds=duration_seconds)

    async def reserve_voice_quota(self, user_id: int) -> None:
        await self.repository.consume_voice_quota(user_id=user_id)
