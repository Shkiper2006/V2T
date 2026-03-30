from app.repositories.subscription_repository import SubscriptionRepository


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    async def subscribe(self, user_id: int) -> str:
        await self.repository.activate_subscription(user_id=user_id)
        return "Подписка активирована ✅"

    async def tariffs(self) -> str:
        return "Тарифы: Basic, Pro, Team"
