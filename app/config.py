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

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_path: str = Field(default="/tmp/v2t_storage", alias="LOCAL_STORAGE_PATH")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="", alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="", alias="S3_SECRET_ACCESS_KEY")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")

    tariff_basic_max_voice_seconds: int = Field(default=300, alias="TARIFF_BASIC_MAX_VOICE_SECONDS")
    tariff_pro_max_voice_seconds: int = Field(default=1800, alias="TARIFF_PRO_MAX_VOICE_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
