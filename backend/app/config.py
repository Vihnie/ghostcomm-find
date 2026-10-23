from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret: SecretStr = Field(min_length=32)
    database_url: str = "sqlite:///./data/campus.db"
    app_timezone: str = "Africa/Nairobi"
    media_dir: Path = Path("data/media")
    frontend_dir: Path | None = None
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-flash-latest"
    campus_email_domains: str = ""
    cors_origins: list[str] = []
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)

    @field_validator("database_url")
    @classmethod
    def select_postgres_driver(cls, value: str) -> str:
        if value.startswith(("postgres://", "postgresql://")):
            return "postgresql+psycopg://" + value.split("://", 1)[1]
        return value

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(
                "APP_TIMEZONE must be a valid IANA timezone, such as Africa/Nairobi"
            ) from None
        return value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.jwt_secret.get_secret_value().startswith("replace-with"):
        raise ValueError("Set JWT_SECRET to a random secret before starting the server")
    return settings
