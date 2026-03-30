from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "V2T"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_url: str = Field(default="http://localhost:8000/auth/google/callback", alias="GOOGLE_REDIRECT_URL")

    database_url: str = Field(default="postgresql+asyncpg://v2t:change-me@localhost:5432/v2t", alias="DATABASE_URL")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_path: str = Field(default="/tmp/v2t_storage", alias="LOCAL_STORAGE_PATH")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="", alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="", alias="S3_SECRET_ACCESS_KEY")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")

    tariff_basic_max_voice_seconds: int = Field(default=300, alias="TARIFF_BASIC_MAX_VOICE_SECONDS")
    tariff_pro_max_voice_seconds: int = Field(default=1800, alias="TARIFF_PRO_MAX_VOICE_SECONDS")

    stt_provider: str = Field(default="vosk", alias="STT_PROVIDER")
    stt_fallback_providers: str = Field(default="faster_whisper,google,yandex", alias="STT_FALLBACK_PROVIDERS")
    stt_default_language: str = Field(default="ru-RU", alias="STT_DEFAULT_LANGUAGE")

    stt_vosk_model_path: str = Field(default="", alias="STT_VOSK_MODEL_PATH")
    stt_faster_whisper_model_size: str = Field(default="small", alias="STT_FASTER_WHISPER_MODEL_SIZE")
    stt_faster_whisper_device: str = Field(default="cpu", alias="STT_FASTER_WHISPER_DEVICE")

    stt_google_api_key: str = Field(default="", alias="STT_GOOGLE_API_KEY")
    stt_yandex_api_key: str = Field(default="", alias="STT_YANDEX_API_KEY")
    stt_yandex_folder_id: str = Field(default="", alias="STT_YANDEX_FOLDER_ID")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
