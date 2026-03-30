from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from celery import chain

from app.celery_app import celery_app
from app.config import get_settings
from app.services.telegram_notifier import TelegramNotifier
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()
storage = StorageService()
notifier = TelegramNotifier()


class TemporaryTaskError(RuntimeError):
    """Represents retryable temporary task errors."""


def _tariff_limit_seconds(tariff: str) -> int:
    return (
        settings.tariff_pro_max_voice_seconds
        if tariff.lower() == "pro"
        else settings.tariff_basic_max_voice_seconds
    )


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

        transcript = f"Транскрипция готова для файла {Path(file_uri).name}"
        logger.info("Voice transcription completed", extra={"user_id": user_id, "status": "success"})

        notifier.send_message(user_id, f"✅ Транскрипция:\n{transcript}")
        chain(create_note.s(user_id=user_id), notify_success.s(user_id=user_id)).delay()
        return {"status": "completed", "transcript": transcript}
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
    note = f"Краткая заметка: {transcript}"
    logger.info("Note created", extra={"user_id": user_id})
    return {"status": "note_created", "note": note}


@celery_app.task(name="app.tasks.transcription.notify_success")
def notify_success(note_result: dict, user_id: int) -> None:
    note = note_result.get("note", "")
    notifier.send_message(user_id, f"📝 Заметка сформирована:\n{note}")
    logger.info("User notified", extra={"user_id": user_id, "status": "notified"})
