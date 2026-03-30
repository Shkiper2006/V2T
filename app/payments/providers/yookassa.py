from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

from app.config import get_settings
from app.payments.providers.base import NormalizedWebhook


class YooKassaAdapter:
    name = "yookassa"

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify_signature(self, payload: dict, signature: str) -> bool:
        secret = self.settings.payments_yookassa_webhook_secret.encode("utf-8")
        data = str(payload.get("object", {}).get("id", "")).encode("utf-8")
        expected = hmac.new(secret, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> NormalizedWebhook:
        obj = payload.get("object", {})
        metadata = obj.get("metadata", {})
        return NormalizedWebhook(
            provider=self.name,
            payment_id=str(obj.get("id", "")),
            telegram_user_id=int(metadata.get("telegram_user_id", 0)),
            status="paid" if obj.get("status") == "succeeded" else "pending",
            amount=Decimal(str(obj.get("amount", {}).get("value", "0"))),
            currency=str(obj.get("amount", {}).get("currency", "RUB")),
            tariff_code=str(metadata.get("tariff", "basic")),
            payload=payload,
        )

    def create_payment_session(self, *, telegram_user_id: int, tariff_code: str, amount: Decimal, currency: str) -> dict:
        return {
            "provider": self.name,
            "payment_url": f"https://yookassa.example/pay/{telegram_user_id}/{tariff_code}",
            "amount": str(amount),
            "currency": currency,
        }
