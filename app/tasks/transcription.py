from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from celery import chain

from app.celery_app import celery_app
from app.config import get_settings
from app.google.note_sync_service import GoogleNoteSyncService, GoogleNoteSyncServiceError
from app.repositories.stt_attempt_log_repository import STTAttemptLogRepository
from app.services.speech_to_text import SpeechProviderError, transcribe_with_fallback
from app.repositories.note_repository import NoteRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.telegram_notifier import TelegramNotifier
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()
storage = StorageService()
notifier = TelegramNotifier()
subscription_repository = SubscriptionRepository()
note_repository = NoteRepository()
stt_attempt_log_repository = STTAttemptLogRepository()
google_sync_service = GoogleNoteSyncService(subscription_repository=subscription_repository)


class TemporaryTaskError(RuntimeError):
    """Represents retryable temporary task errors."""


def _parse_request_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(tz=timezone.utc)

    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_google_sync_retryable(exc: GoogleNoteSyncServiceError) -> bool:
    message = str(exc).lower()
    retryable_markers = ("api unavailable", "http 429", "http 500", "http 502", "http 503", "http 504")
    return any(marker in message for marker in retryable_markers)


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
    request_timestamp = payload.get("timestamp")

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

        chain(
            create_note.s(
                {
                    "transcript": transcript,
                    "provider": transcription_result.provider,
                    "duration": duration,
                    "user_id": user_id,
                    "timestamp": request_timestamp or datetime.now(tz=timezone.utc).isoformat(),
                    "stt_duration_seconds": transcription_result.duration_seconds,
                }
            ),
            notify_success.s(user_id=user_id),
        ).delay()
        return {
            "status": "completed",
            "transcript": transcript,
            "provider": transcription_result.provider,
            "language": language or settings.stt_default_language,
            "duration": duration,
        }
    except SpeechProviderError as exc:
        logger.exception("STT failed", extra={"user_id": user_id, "error_code": exc.code, "retryable": exc.retryable})
        if exc.retryable:
            notifier.send_message(user_id, "⚠️ Временная ошибка распознавания речи, пробуем снова...")
            raise TemporaryTaskError(str(exc)) from exc
        notifier.send_message(user_id, f"❌ Ошибка распознавания речи ({exc.code}). Попробуйте позже.")
        raise
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


@celery_app.task(
    bind=True,
    name="app.tasks.transcription.create_note",
    autoretry_for=(TemporaryTaskError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def create_note(self, transcript_result: dict) -> dict:
    transcript = transcript_result.get("transcript", "")
    provider = transcript_result.get("provider", "unknown")
    duration_seconds = int(transcript_result.get("duration", 0))
    user_id = int(transcript_result["user_id"])
    request_timestamp = _parse_request_timestamp(transcript_result.get("timestamp"))
    stt_duration_seconds = float(transcript_result.get("stt_duration_seconds", 0.0))

    try:
        google_destination = google_sync_service.sync_note(telegram_user_id=user_id, text=transcript)
    except GoogleNoteSyncServiceError as exc:
        retryable = _is_google_sync_retryable(exc)
        logger.exception(
            "Google sync failed",
            extra={"user_id": user_id, "provider": provider, "retryable": retryable},
        )
        if retryable:
            notifier.send_message(user_id, "⚠️ Временная ошибка записи в Google, пробуем снова...")
            raise TemporaryTaskError(str(exc)) from exc

        asyncio.run(
            stt_attempt_log_repository.create(
                user_id=user_id,
                provider=provider,
                success=False,
                retryable=False,
                error_code="GOOGLE_SYNC_FAILED",
                stt_duration_seconds=stt_duration_seconds,
                audio_duration_seconds=duration_seconds,
                request_timestamp=request_timestamp,
            )
        )
        return {
            "status": "failed",
            "transcript": transcript,
            "duration": duration_seconds,
            "google_destination": "failed",
        }

    async def _save_fact() -> None:
        user = await subscription_repository.get_user(user_id=user_id)
        await note_repository.create(user_id=user.id, text=transcript, duration_seconds=duration_seconds)
        await stt_attempt_log_repository.create(
            user_id=user.id,
            provider=provider,
            success=True,
            retryable=False,
            error_code=None,
            stt_duration_seconds=stt_duration_seconds,
            audio_duration_seconds=duration_seconds,
            request_timestamp=request_timestamp,
        )

    asyncio.run(_save_fact())
    logger.info("Google note created", extra={"user_id": user_id, "google_destination": google_destination})
    return {
        "status": "note_created",
        "transcript": transcript,
        "duration": duration_seconds,
        "google_destination": google_destination,
    }


@celery_app.task(name="app.tasks.transcription.notify_success")
def notify_success(note_result: dict, user_id: int) -> None:
    status = note_result.get("status", "unknown")
    if status != "note_created":
        notifier.send_message(user_id, "❌ Не удалось записать заметку в Google Docs/Sheets.")
        logger.warning("User notified about failed note sync", extra={"user_id": user_id, "status": status})
        return

    transcript = note_result.get("transcript", "")
    duration = int(note_result.get("duration", 0))
    google_destination = note_result.get("google_destination", "unknown")
    notifier.send_message(
        user_id,
        (
            "📝 Готово! Запись сохранена.\n"
            f"Текст: {transcript}\n"
            f"Время: {duration} сек.\n"
            f"Google: {google_destination}"
        ),
    )
    logger.info("User notified", extra={"user_id": user_id, "status": "notified"})
