import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.repositories.subscription_repository import SubscriptionRepository
from app.services.storage_service import StorageService
from app.services.subscription_service import SubscriptionService
from app.tasks.transcription import process_voice

logger = logging.getLogger(__name__)
router = Router(name="telegram_commands")
service = SubscriptionService(repository=SubscriptionRepository())
storage = StorageService()


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


@router.message(lambda msg: bool(msg.voice))
async def voice_message_handler(message: Message) -> None:
    if message.voice is None:
        return

    file_info = await message.bot.get_file(message.voice.file_id)
    file_data = await message.bot.download_file(file_info.file_path)
    voice_bytes = file_data.read()

    file_uri = storage.save_bytes(data=voice_bytes, suffix=".ogg")
    tariff = await service.user_tariff(user_id=message.from_user.id)

    payload = {
        "telegram_user_id": message.from_user.id,
        "file_uri": file_uri,
        "duration": message.voice.duration,
        "tariff": tariff,
    }

    process_voice.delay(payload)
    logger.info("Voice task queued", extra={"user_id": message.from_user.id, "file_uri": file_uri})
    await message.answer("🎧 Голосовое сообщение получено. Начинаю обработку...")
