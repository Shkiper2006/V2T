from app.models.user import User


class SubscriptionRepository:
    async def activate_subscription(self, user_id: int) -> User:
        # Stub method for database persistence.
        return User(id=user_id, telegram_id=str(user_id), is_subscribed=True)
