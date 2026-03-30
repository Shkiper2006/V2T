from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.payment_service import PaymentService


class PaymentWebhookService:
    def __init__(self) -> None:
        self.payment_service = PaymentService(
            payment_repository=PaymentRepository(),
            subscription_repository=SubscriptionRepository(),
        )

    async def handle(self, provider: str, payload: dict, signature: str) -> None:
        await self.payment_service.handle_webhook(provider=provider, payload=payload, signature=signature)
