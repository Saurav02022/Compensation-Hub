from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and an optional `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: PostgresDsn
    log_level: str = "INFO"

    # Ask Compensation is optional: without a Gemini API key the feature reports itself
    # unavailable while every other workflow keeps working.
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = 20.0
    gemini_thinking_level: Literal["low", "medium", "high"] = "low"

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def blank_key_means_unconfigured(cls, value: object) -> object:
        # `GEMINI_API_KEY=` in an env file or compose environment must not enable the feature.
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
