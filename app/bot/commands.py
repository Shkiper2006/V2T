import logging
from datetime import UTC
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.i18n import get_locale, t
from app.bot.keyboards import main_menu_keyboard, payment_select_keyboard, tariff_select_keyboard
from app.google.oauth import GoogleOAuthService
from app.repositories.note_repository import NoteRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.payment_service import PaymentService
from app.services.storage_service import StorageService
from app.services.subscription_service import SubscriptionService
from app.tasks.transcription import process_voice

logger = logging.getLogger(__name__)
router = Router(name="telegram_commands")
service = SubscriptionService(repository=SubscriptionRepository())
payment_service = PaymentService(
    payment_repository=PaymentRepository(),
    subscription_repository=SubscriptionRepository(),
)
google_oauth_service = GoogleOAuthService()
storage = StorageService()
note_repository = NoteRepository()
UNLIMITED_QUOTA = 1_000_000

HISTORY_LIMITS_BY_TARIFF: dict[str, int] = {
    "free": 5,
    "basic": 5,
    "pro": 20,
    "business": 100,
}


@router.message(Command("start"))
async def start_cmd(message: Message) -> None:
    user_id = message.from_user.id
    locale = get_locale(message.from_user.language_code if message.from_user else None)

    google_connected = await service.is_google_connected(user_id=user_id)
    tariff = await service.user_tariff(user_id=user_id)
    quota = await service.quota_status(user_id=user_id)

    steps = [
        t("welcome", locale),
        "1) "
        + (
            t("start_step_google_connected", locale)
            if google_connected
            else t("start_step_google_missing", locale)
        ),
        t("start_step_tariff", locale, tariff=tariff.upper()),
        t("start_step_quota", locale, remaining=quota["remaining"], quota=quota["quota"]),
        t("start_step_end", locale),
    ]
    await message.answer("\n".join(steps), reply_markup=main_menu_keyboard())


@router.message(Command("subscribe"))
async def subscribe_cmd(message: Message) -> None:
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    await message.answer(t("subscribe_title", locale), reply_markup=tariff_select_keyboard())


@router.message(Command("tariffs"))
async def tariffs_cmd(message: Message) -> None:
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    tariffs = await service.tariffs_catalog()

    lines = [t("tariffs_title", locale)]
    for tariff in tariffs:
        quota_value = int(tariff["quota"])
        quota_text = "безлимит" if quota_value >= UNLIMITED_QUOTA else str(quota_value)
        lines.append(
            f"• {tariff['title']} (~{int(tariff['price'])}₽/мес): "
            f"{quota_text} сообщений, до {int(tariff['max_audio'])}s, "
            f"приоритет {tariff['priority_display']}. {tariff['features']}."
        )

    await message.answer("\n".join(lines), reply_markup=tariff_select_keyboard())


@router.message(Command("limits"))
async def limits_cmd(message: Message) -> None:
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    tariff = await service.user_tariff_details(user_id=message.from_user.id)
    quota_value = int(tariff["quota"])
    quota_text = "безлимит" if quota_value >= UNLIMITED_QUOTA else f"{quota_value}"
    lines = [
        t("limits_header", locale, title=str(tariff["title"]), code=str(tariff["code"]).upper()),
        f"Лимиты: {quota_text} сообщений/мес, до {int(tariff['max_audio'])}s, "
        f"приоритет очереди: {tariff['priority_display']}.",
        f"План: {tariff['features']}.",
        f"Цена: ~{int(tariff['price'])}₽/мес.",
    ]
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("plan:"))
async def select_plan_callback(callback: CallbackQuery) -> None:
    locale = get_locale(callback.from_user.language_code if callback.from_user else None)
    tariff_code = callback.data.split(":", maxsplit=1)[1]
    await callback.message.answer(
        t("payment_title", locale),
        reply_markup=payment_select_keyboard(tariff_code=tariff_code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:"))
async def pay_callback(callback: CallbackQuery) -> None:
    locale = get_locale(callback.from_user.language_code if callback.from_user else None)
    tariff_code = callback.data.split(":", maxsplit=1)[1]
    session = await payment_service.create_payment_session(
        telegram_user_id=callback.from_user.id,
        tariff_code=tariff_code,
    )
    await callback.message.answer(
        t("payment_link", locale, tariff=tariff_code.upper(), url=session["payment_url"], provider=session["provider"])
    )
    await callback.answer()


@router.message(Command("connect_google"))
async def connect_google_cmd(message: Message) -> None:
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    auth_url = google_oauth_service.build_auth_url(telegram_user_id=message.from_user.id)
    await message.answer(t("connect_google_message", locale, url=auth_url))


@router.message(Command("history"))
async def history_cmd(message: Message) -> None:
    requested_count = 5
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].isdigit():
            requested_count = int(parts[1])

    user_id = message.from_user.id
    is_active, inactive_reason = await service.ensure_active_subscription(user_id=user_id)
    if not is_active:
        await message.answer(f"❌ {inactive_reason}")
        return

    tariff = await service.user_tariff(user_id=user_id)
    tariff_limit = HISTORY_LIMITS_BY_TARIFF.get(tariff.lower(), HISTORY_LIMITS_BY_TARIFF["free"])
    notes_limit = max(1, min(requested_count, tariff_limit))
    notes = await note_repository.list_by_user(
        user_id=user_id,
        page=1,
        page_size=notes_limit,
        sort="desc",
    )

    if not notes:
        await message.answer(t("history_empty", locale))
        return

    if requested_count > tariff_limit:
        await message.answer(
            f"ℹ️ По тарифу {tariff} доступно до {tariff_limit} заметок за запрос. Показываю {notes_limit}."
        )

    lines = [t("history_header", locale, count=len(notes))]
    for idx, note in enumerate(notes, start=1):
        created_at = note.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        stamp = created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"{idx}. [{stamp}] {note.text}")

    await message.answer("\n".join(lines))


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    locale = get_locale(message.from_user.language_code if message.from_user else None)
    await message.answer(t("help", locale))


@router.message(F.text == "Тарифы")
async def tariffs_button_handler(message: Message) -> None:
    await tariffs_cmd(message)


@router.message(F.text == "Подключить Google")
async def google_button_handler(message: Message) -> None:
    await connect_google_cmd(message)


@router.message(F.text == "История")
async def history_button_handler(message: Message) -> None:
    await history_cmd(message)


@router.message(F.text == "Подписка")
async def subscribe_button_handler(message: Message) -> None:
    await subscribe_cmd(message)


@router.message(lambda msg: bool(msg.voice))
async def voice_message_handler(message: Message) -> None:
    if message.voice is None:
        return

    is_active, inactive_reason = await service.ensure_active_subscription(user_id=message.from_user.id)
    if not is_active:
        await message.answer(f"❌ {inactive_reason}")
        return

    file_info = await message.bot.get_file(message.voice.file_id)
    file_data = await message.bot.download_file(file_info.file_path)
    voice_bytes = file_data.read()

    file_uri = storage.save_bytes(data=voice_bytes, suffix=".ogg")
    tariff = await service.user_tariff_details(user_id=message.from_user.id)
    allowed, reason = await service.check_voice_allowed(
        user_id=message.from_user.id,
        duration_seconds=message.voice.duration,
    )
    if not allowed:
        await message.answer(f"❌ {reason}")
        return

    payload = {
        "request_id": str(uuid4()),
        "telegram_user_id": message.from_user.id,
        "file_uri": file_uri,
        "duration": message.voice.duration,
        "tariff": tariff["code"],
    }

    queue_priority = str(tariff["queue_priority"])
    if queue_priority not in {"low", "normal", "high", "business"}:
        queue_priority = "normal"
    queue_name = f"transcription_{queue_priority}"
    process_voice.apply_async(args=(payload,), queue=queue_name)
    logger.info("Voice task queued", extra={"user_id": message.from_user.id, "file_uri": file_uri})
    await message.answer(
        "🎧 Голосовое сообщение получено. Начинаю обработку...\n"
        f"Приоритет очереди: {queue_priority}."
    )
