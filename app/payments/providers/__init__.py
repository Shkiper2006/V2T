from app.payments.providers.base import NormalizedWebhook, PaymentProviderAdapter
from app.payments.providers.cloudpayments import CloudPaymentsAdapter
from app.payments.providers.robokassa import RobokassaAdapter
from app.payments.providers.yookassa import YooKassaAdapter


def get_provider_adapter(provider: str) -> PaymentProviderAdapter:
    normalized = provider.lower()
    providers: dict[str, PaymentProviderAdapter] = {
        "yookassa": YooKassaAdapter(),
        "cloudpayments": CloudPaymentsAdapter(),
        "robokassa": RobokassaAdapter(),
    }
    if normalized not in providers:
        raise ValueError(f"Unsupported payment provider: {provider}")
    return providers[normalized]


__all__ = [
    "NormalizedWebhook",
    "PaymentProviderAdapter",
    "YooKassaAdapter",
    "CloudPaymentsAdapter",
    "RobokassaAdapter",
    "get_provider_adapter",
]
