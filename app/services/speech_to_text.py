from __future__ import annotations

import abc
import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("app.transcription.audit")
settings = get_settings()


class SpeechProviderError(RuntimeError):
    """Base exception for STT providers."""

    def __init__(self, message: str, code: str = "UNKNOWN", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ProviderUnavailableError(SpeechProviderError):
    """Raised when provider cannot be used in current environment."""


class SpeechToTextService(abc.ABC):
    """Abstract speech-to-text provider."""

    provider_name: str

    @abc.abstractmethod
    def transcribe(self, file_path: str) -> str:
        """Transcribe local audio file and return plain text."""


class VoskSpeechService(SpeechToTextService):
    provider_name = "vosk"

    def __init__(self, language: str = "ru") -> None:
        self.language = language

    def transcribe(self, file_path: str) -> str:
        try:
            import vosk
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailableError("vosk package is not installed", code="PROVIDER_UNAVAILABLE") from exc

        model_path = settings.stt_vosk_model_path
        if not model_path:
            raise ProviderUnavailableError("Vosk model path is not configured", code="CONFIG_MISSING")

        wav_file = Path(file_path)
        if not wav_file.exists():
            raise SpeechProviderError("Audio file does not exist", code="FILE_NOT_FOUND")

        try:
            model = vosk.Model(model_path=model_path)
            recognizer = vosk.KaldiRecognizer(model, 16000)
            with wave.open(str(wav_file), "rb") as stream:
                while True:
                    chunk = stream.readframes(4000)
                    if not chunk:
                        break
                    recognizer.AcceptWaveform(chunk)

            text = json.loads(recognizer.FinalResult()).get("text", "").strip()
            if not text:
                raise SpeechProviderError("Vosk returned empty transcript", code="EMPTY_RESULT")
            return text
        except SpeechProviderError:
            raise
        except Exception as exc:
            raise SpeechProviderError(str(exc), code="VOSK_FAILED") from exc


class FasterWhisperSpeechService(SpeechToTextService):
    provider_name = "faster_whisper"

    def __init__(self, language: str = "ru") -> None:
        self.language = language

    def transcribe(self, file_path: str) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailableError(
                "faster-whisper package is not installed",
                code="PROVIDER_UNAVAILABLE",
            ) from exc

        try:
            model = WhisperModel(
                settings.stt_faster_whisper_model_size,
                device=settings.stt_faster_whisper_device,
                compute_type="int8",
            )
            segments, _ = model.transcribe(file_path, language=self.language)
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if not text:
                raise SpeechProviderError("FasterWhisper returned empty transcript", code="EMPTY_RESULT")
            return text
        except SpeechProviderError:
            raise
        except Exception as exc:
            raise SpeechProviderError(str(exc), code="FASTER_WHISPER_FAILED") from exc


class GoogleSpeechToTextService(SpeechToTextService):
    provider_name = "google"

    def __init__(self, language: str = "ru-RU") -> None:
        self.language = language

    def transcribe(self, file_path: str) -> str:
        api_key = settings.stt_google_api_key
        if not api_key:
            raise ProviderUnavailableError("Google API key is not configured", code="CONFIG_MISSING")

        content = Path(file_path).read_bytes()
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "languageCode": self.language,
                "enableAutomaticPunctuation": True,
            },
            "audio": {"content": base64.b64encode(content).decode("utf-8")},
        }

        request = urllib.request.Request(
            f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SpeechProviderError(f"Google STT HTTP {exc.code}", code=f"HTTP_{exc.code}") from exc
        except Exception as exc:
            raise SpeechProviderError(str(exc), code="GOOGLE_FAILED") from exc

        alternatives = (body.get("results") or [{}])[0].get("alternatives") or []
        text = alternatives[0].get("transcript", "").strip() if alternatives else ""
        if not text:
            raise SpeechProviderError("Google returned empty transcript", code="EMPTY_RESULT")
        return text


class YandexSpeechKitService(SpeechToTextService):
    provider_name = "yandex"

    def __init__(self, language: str = "ru-RU") -> None:
        self.language = language

    def transcribe(self, file_path: str) -> str:
        api_key = settings.stt_yandex_api_key
        if not api_key:
            raise ProviderUnavailableError("Yandex API key is not configured", code="CONFIG_MISSING")

        query = urllib.parse.urlencode(
            {
                "topic": "general",
                "lang": self.language,
                "folderId": settings.stt_yandex_folder_id,
            }
        )
        request = urllib.request.Request(
            f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{query}",
            data=Path(file_path).read_bytes(),
            headers={"Authorization": f"Api-Key {api_key}"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SpeechProviderError(f"Yandex STT HTTP {exc.code}", code=f"HTTP_{exc.code}") from exc
        except Exception as exc:
            raise SpeechProviderError(str(exc), code="YANDEX_FAILED") from exc

        text = body.get("result", "").strip()
        if not text:
            raise SpeechProviderError("Yandex returned empty transcript", code="EMPTY_RESULT")
        return text


@dataclass(frozen=True)
class STTAttemptResult:
    transcript: str | None
    provider: str
    success: bool
    duration_seconds: float
    error_code: str | None = None


class SpeechToTextFactory:
    _providers: dict[str, type[SpeechToTextService]] = {
        "vosk": VoskSpeechService,
        "faster_whisper": FasterWhisperSpeechService,
        "google": GoogleSpeechToTextService,
        "yandex": YandexSpeechKitService,
    }

    @classmethod
    def provider_order(cls) -> list[str]:
        primary = settings.stt_provider.strip().lower()
        configured_fallbacks = [
            provider.strip().lower()
            for provider in settings.stt_fallback_providers.split(",")
            if provider.strip()
        ]

        ordered = [primary] + configured_fallbacks
        return [provider for provider in ordered if provider in cls._providers]

    @classmethod
    def create(cls, provider_name: str, language: str) -> SpeechToTextService:
        service_class = cls._providers.get(provider_name)
        if not service_class:
            raise ProviderUnavailableError(f"Unknown STT provider: {provider_name}", code="UNKNOWN_PROVIDER")
        return service_class(language=language)


def normalize_language(language: str | None) -> str:
    if language and language.strip():
        return language.strip()
    return settings.stt_default_language


def transcribe_with_fallback(file_path: str, language: str | None = None) -> STTAttemptResult:
    target_language = normalize_language(language)
    attempts: list[STTAttemptResult] = []

    for provider_name in SpeechToTextFactory.provider_order():
        start = time.perf_counter()
        try:
            service = SpeechToTextFactory.create(provider_name, target_language)
            transcript = service.transcribe(file_path)
            elapsed = time.perf_counter() - start
            result = STTAttemptResult(
                transcript=transcript,
                provider=provider_name,
                success=True,
                duration_seconds=elapsed,
            )
            _log_attempt(result)
            return result
        except SpeechProviderError as exc:
            elapsed = time.perf_counter() - start
            failure = STTAttemptResult(
                transcript=None,
                provider=provider_name,
                success=False,
                duration_seconds=elapsed,
                error_code=exc.code,
            )
            attempts.append(failure)
            _log_attempt(failure)
            logger.warning("STT provider failed", extra={"provider": provider_name, "error_code": exc.code})

    last_error = attempts[-1].error_code if attempts else "NO_PROVIDER"
    raise SpeechProviderError("All STT providers failed", code=last_error or "STT_FAILED")


def _log_attempt(result: STTAttemptResult) -> None:
    audit_logger.info(
        "stt_attempt",
        extra={
            "provider": result.provider,
            "duration_seconds": round(result.duration_seconds, 3),
            "success": result.success,
            "error_code": result.error_code,
        },
    )
