"""Typed application settings loaded from environment variables (and `.env` in development)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL

REPO_ROOT = Path(__file__).resolve().parents[3]
PLACEHOLDER_PREFIX = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nebula API"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    jwt_secret: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)

    postgres_user: str = "nebula"
    postgres_password: SecretStr
    postgres_db: str = "nebula"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _reject_placeholders_in_production(self) -> Self:
        if self.is_production:
            if self.jwt_secret.get_secret_value().startswith(PLACEHOLDER_PREFIX):
                raise ValueError("JWT_SECRET still has its placeholder value")
            if self.postgres_password.get_secret_value().startswith(PLACEHOLDER_PREFIX):
                raise ValueError("POSTGRES_PASSWORD still has its placeholder value")
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
