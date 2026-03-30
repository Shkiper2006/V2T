from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from celery import chain

from app.celery_app import celery_app
from app.config import get_settings
from app.google.note_sync_service import GoogleNoteSyncService, GoogleNoteSyncServiceError
from app.services.speech_to_text import transcribe_with_fallback
from app.repositories.note_repository import NoteRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.note_service import NoteService
from app.services.telegram_notifier import TelegramNotifier
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()
storage = StorageService()
notifier = TelegramNotifier()
subscription_repository = SubscriptionRepository()
note_repository = NoteRepository()

note_service = NoteService(
    note_repository=note_repository,
    subscription_repository=subscription_repository,
)
google_sync_service = GoogleNoteSyncService(subscription_repository=subscription_repository)


class TemporaryTaskError(RuntimeError):
    """Represents retryable temporary task errors."""


def _tariff_limit_seconds(tariff: str) -> int:
    async def _get_limit() -> int:
        tariff_obj = await subscription_repository.get_tariff(tariff.lower())
        if tariff_obj is None:
            return settings.tariff_basic_max_voice_seconds
        return tariff_obj.max_audio_seconds

    return asyncio.run(_get_limit())


@celery_app.task(
    bind=True,
    name="app.tasks.transcription.process_voice",
    autoretry_for=(TemporaryTaskError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def process_voice(self, payload: dict) -> dict:
    user_id = payload["telegram_user_id"]
    tariff = payload.get("tariff", "basic")
    duration = int(payload.get("duration", 0))
    file_uri = payload["file_uri"]
    language = payload.get("language")

    logger.info("Voice processing started", extra={"user_id": user_id, "file_uri": file_uri})

    max_duration = _tariff_limit_seconds(tariff)
    if duration > max_duration:
        msg = f"Длительность {duration}s превышает лимит тарифа {tariff}: {max_duration}s"
        logger.warning(msg, extra={"user_id": user_id})
        notifier.send_message(user_id, f"❌ {msg}")
        raise ValueError(msg)

    try:
        ogg_bytes = storage.download_bytes(file_uri)
        with NamedTemporaryFile(suffix=".ogg", delete=False) as src:
            src.write(ogg_bytes)
            ogg_path = Path(src.name)

        wav_path = ogg_path.with_suffix(".wav")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(ogg_path), str(wav_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error("ffmpeg conversion failed: %s", result.stderr)
            raise TemporaryTaskError("ffmpeg conversion failed")

        transcription_result = transcribe_with_fallback(str(wav_path), language=language)
        transcript = transcription_result.transcript or ""
        logger.info("Voice transcription completed", extra={"user_id": user_id, "status": "success"})

        notifier.send_message(user_id, f"✅ Транскрипция:\n{transcript}")
        chain(create_note.s(user_id=user_id), notify_success.s(user_id=user_id)).delay()
        return {
            "status": "completed",
            "transcript": transcript,
            "provider": transcription_result.provider,
            "language": language or settings.stt_default_language,
            "duration": duration,
        }
    except TemporaryTaskError:
        notifier.send_message(user_id, "⚠️ Временная ошибка обработки, пробуем снова...")
        raise
    except Exception as exc:
        logger.exception("Voice processing failed", extra={"user_id": user_id})
        notifier.send_message(user_id, f"❌ Ошибка обработки: {exc}")
        raise
    finally:
        if "ogg_path" in locals() and ogg_path.exists():
            ogg_path.unlink(missing_ok=True)
        if "wav_path" in locals() and wav_path.exists():
            wav_path.unlink(missing_ok=True)


@celery_app.task(name="app.tasks.transcription.create_note")
def create_note(transcript_result: dict, user_id: int) -> dict:
    transcript = transcript_result.get("transcript", "")
    duration_seconds = int(transcript_result.get("duration", 0))
    note_text = asyncio.run(
        note_service.create_summary_note(
            telegram_user_id=user_id,
            transcript=transcript,
            duration_seconds=duration_seconds,
        )
    )

    google_status = "not_configured"
    google_error: str | None = None
    try:
        sync_mode = google_sync_service.sync_note(telegram_user_id=user_id, text=note_text)
        google_status = f"created_in_{sync_mode}"
        fact_text = f"Google заметка успешно создана в режиме {sync_mode}: {note_text[:180]}"
    except GoogleNoteSyncServiceError as exc:
        google_status = "failed"
        google_error = str(exc)
        fact_text = f"Google заметка не создана: {exc}"

    async def _save_fact() -> None:
        user = await subscription_repository.get_user(user_id=user_id)
        await note_repository.create(user_id=user.id, text=fact_text)

    asyncio.run(_save_fact())

    logger.info("Note created", extra={"user_id": user_id, "google_status": google_status})
    return {
        "status": "note_created",
        "note": note_text,
        "google_status": google_status,
        "google_error": google_error,
    }


@celery_app.task(name="app.tasks.transcription.notify_success")
def notify_success(note_result: dict, user_id: int) -> None:
    note = note_result.get("note", "")
    google_status = note_result.get("google_status", "unknown")
    notifier.send_message(user_id, f"📝 Заметка сформирована:\n{note}\n\nGoogle sync: {google_status}")
    logger.info("User notified", extra={"user_id": user_id, "status": "notified"})
