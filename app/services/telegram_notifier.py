import asyncio

from aiogram import Bot

from app.config import get_settings


class TelegramNotifier:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_message(self, telegram_user_id: int, text: str) -> None:
        if not self.settings.telegram_bot_token:
            return

        async def _send() -> None:
            bot = Bot(token=self.settings.telegram_bot_token)
            try:
                await bot.send_message(chat_id=telegram_user_id, text=text)
            finally:
                await bot.session.close()

        asyncio.run(_send())
