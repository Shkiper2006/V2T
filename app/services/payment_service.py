from __future__ import annotations

from decimal import Decimal

from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository, subscription_repository: SubscriptionRepository) -> None:
        self.payment_repository = payment_repository
        self.subscription_repository = subscription_repository

    async def handle_webhook(self, payload: dict) -> None:
        telegram_user_id = int(payload.get("telegram_user_id", 0))
        if telegram_user_id <= 0:
            return

        user = await self.subscription_repository.get_user(user_id=telegram_user_id)
        payment = await self.payment_repository.create_or_update(
            user_id=user.id,
            provider=str(payload.get("provider", "unknown")),
            external_payment_id=str(payload.get("payment_id", "")),
            status=str(payload.get("status", "pending")),
            amount=Decimal(str(payload.get("amount", 0))),
            currency=str(payload.get("currency", "RUB")),
            payload=payload,
        )

        if payment.status == "paid":
            await self.subscription_repository.activate_subscription(user_id=telegram_user_id)
