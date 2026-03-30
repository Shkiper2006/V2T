from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService

router = Router(name="telegram_commands")
service = SubscriptionService(repository=SubscriptionRepository())


@router.message(Command("start"))
async def start_cmd(message: Message) -> None:
    await message.answer("Добро пожаловать! Используйте /help для списка команд.")


@router.message(Command("subscribe"))
async def subscribe_cmd(message: Message) -> None:
    response = await service.subscribe(user_id=message.from_user.id)
    await message.answer(response)


@router.message(Command("tariffs"))
async def tariffs_cmd(message: Message) -> None:
    await message.answer(await service.tariffs())


@router.message(Command("connect_google"))
async def connect_google_cmd(message: Message) -> None:
    await message.answer("Подключение Google: откройте /auth/google")


@router.message(Command("history"))
async def history_cmd(message: Message) -> None:
    await message.answer("История операций пока пуста.")


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "Доступные команды:\n"
        "/start\n"
        "/subscribe\n"
        "/tariffs\n"
        "/connect_google\n"
        "/history\n"
        "/help"
    )
