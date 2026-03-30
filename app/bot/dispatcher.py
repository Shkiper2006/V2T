from aiogram import Bot, Dispatcher

from app.bot.commands import router
from app.config import get_settings

settings = get_settings()
bot = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None

dp = Dispatcher()
dp.include_router(router)
