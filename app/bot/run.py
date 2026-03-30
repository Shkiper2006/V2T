import asyncio

from app.bot.dispatcher import bot, dp


async def main() -> None:
    if bot is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
