from __future__ import annotations

import hashlib
from decimal import Decimal

from app.config import get_settings
from app.payments.providers.base import NormalizedWebhook


class CloudPaymentsAdapter:
    name = "cloudpayments"

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify_signature(self, payload: dict, signature: str) -> bool:
        secret = self.settings.payments_cloudpayments_secret
        source = f"{payload.get('InvoiceId', '')}:{secret}"
        expected = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return expected == signature

    def parse_webhook(self, payload: dict) -> NormalizedWebhook:
        account_id = str(payload.get("AccountId", "0"))
        tariff_code = str(payload.get("Data", {}).get("tariff", "basic"))
        status = "paid" if str(payload.get("Status", "")).lower() == "completed" else "pending"
        return NormalizedWebhook(
            provider=self.name,
            payment_id=str(payload.get("InvoiceId", "")),
            telegram_user_id=int(account_id),
            status=status,
            amount=Decimal(str(payload.get("Amount", 0))),
            currency=str(payload.get("Currency", "RUB")),
            tariff_code=tariff_code,
            payload=payload,
        )

    def create_payment_session(self, *, telegram_user_id: int, tariff_code: str, amount: Decimal, currency: str) -> dict:
        return {
            "provider": self.name,
            "payment_url": f"https://cloudpayments.example/pay/{telegram_user_id}/{tariff_code}",
            "amount": str(amount),
            "currency": currency,
        }
