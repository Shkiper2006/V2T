from __future__ import annotations

from decimal import Decimal

from app.config import get_settings
from app.payments.providers import get_provider_adapter
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository, subscription_repository: SubscriptionRepository) -> None:
        self.payment_repository = payment_repository
        self.subscription_repository = subscription_repository
        self.settings = get_settings()

    async def handle_webhook(self, provider: str, payload: dict, signature: str) -> None:
        adapter = get_provider_adapter(provider)
        if not adapter.verify_signature(payload=payload, signature=signature):
            raise ValueError("Invalid payment signature")

        event = adapter.parse_webhook(payload)
        if event.telegram_user_id <= 0:
            return

        user = await self.subscription_repository.get_user(user_id=event.telegram_user_id)
        payment = await self.payment_repository.create_or_update(
            user_id=user.id,
            provider=event.provider,
            external_payment_id=event.payment_id,
            status=event.status,
            amount=event.amount,
            currency=event.currency,
            payload=event.payload,
        )

        if payment.status == "paid":
            billing_cycle_days = self._resolve_billing_cycle_days(event.payload)
            await self.subscription_repository.activate_tariff(
                user_id=event.telegram_user_id,
                tariff_code=event.tariff_code,
                billing_cycle_days=billing_cycle_days,
            )

    @staticmethod
    def _resolve_billing_cycle_days(payload: dict) -> int:
        data = payload.get("Data", {}) if isinstance(payload, dict) else {}
        cycle = data.get("billing_cycle_days")
        if cycle is None:
            cycle = data.get("billing_cycle")
        try:
            return max(1, int(cycle))
        except (TypeError, ValueError):
            return 30

    async def create_payment_session(self, telegram_user_id: int, tariff_code: str) -> dict:
        tariff = await self.subscription_repository.get_tariff(tariff_code)
        if tariff is None:
            raise ValueError(f"Tariff '{tariff_code}' not found")

        adapter = get_provider_adapter(self.settings.payments_provider)
        return adapter.create_payment_session(
            telegram_user_id=telegram_user_id,
            tariff_code=tariff_code,
            amount=Decimal(str(tariff.price_rub)),
            currency="RUB",
        )
