from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class NormalizedWebhook:
    provider: str
    payment_id: str
    telegram_user_id: int
    status: str
    amount: Decimal
    currency: str
    tariff_code: str
    payload: dict


class PaymentProviderAdapter(Protocol):
    name: str

    def verify_signature(self, payload: dict, signature: str) -> bool: ...

    def parse_webhook(self, payload: dict) -> NormalizedWebhook: ...

    def create_payment_session(self, *, telegram_user_id: int, tariff_code: str, amount: Decimal, currency: str) -> dict: ...
