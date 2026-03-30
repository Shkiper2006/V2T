from __future__ import annotations

import hashlib
from decimal import Decimal

from app.config import get_settings
from app.payments.providers.base import NormalizedWebhook


class RobokassaAdapter:
    name = "robokassa"

    def __init__(self) -> None:
        self.settings = get_settings()

    def verify_signature(self, payload: dict, signature: str) -> bool:
        invoice_id = str(payload.get("InvId", ""))
        out_sum = str(payload.get("OutSum", "0"))
        base = f"{out_sum}:{invoice_id}:{self.settings.payments_robokassa_password2}"
        expected = hashlib.md5(base.encode("utf-8")).hexdigest().upper()
        return expected == signature.upper()

    def parse_webhook(self, payload: dict) -> NormalizedWebhook:
        shp_telegram = int(payload.get("Shp_telegram_user_id", 0))
        tariff_code = str(payload.get("Shp_tariff", "basic"))
        return NormalizedWebhook(
            provider=self.name,
            payment_id=str(payload.get("InvId", "")),
            telegram_user_id=shp_telegram,
            status="paid",
            amount=Decimal(str(payload.get("OutSum", 0))),
            currency="RUB",
            tariff_code=tariff_code,
            payload=payload,
        )

    def create_payment_session(self, *, telegram_user_id: int, tariff_code: str, amount: Decimal, currency: str) -> dict:
        return {
            "provider": self.name,
            "payment_url": f"https://robokassa.example/pay/{telegram_user_id}/{tariff_code}",
            "amount": str(amount),
            "currency": currency,
        }
