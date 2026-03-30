from dataclasses import dataclass


@dataclass
class User:
    id: int
    telegram_id: str
    is_subscribed: bool = False
