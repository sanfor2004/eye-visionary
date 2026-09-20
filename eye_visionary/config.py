"""Validated runtime configuration for the API and worker."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/eye_visionary"
    redis_url: str = "redis://127.0.0.1:6379/0"
    storage_root: Path = Path("data/images")
    model_cache_root: Path = Path("data/models")
    analysis_version: str = "1"
    face_vector_dimension: Annotated[int, Field(gt=0)] = 512
    max_image_bytes: Annotated[int, Field(gt=0)] = 25_000_000
    worker_concurrency: Annotated[int, Field(gt=0, le=64)] = 1
    max_job_retries: Annotated[int, Field(ge=0, le=10)] = 3
    gps_policy: str = "retain"
    retention_days: int | None = None
    api_keys: SecretStr | None = Field(default=None, validation_alias=AliasChoices("EYE_VISIONARY_API_KEYS", "API_KEYS"))
    allow_anonymous: bool = Field(default=False, validation_alias=AliasChoices("EYE_VISIONARY_ALLOW_ANONYMOUS", "ALLOW_ANONYMOUS"))
    offline: bool = Field(default=False, validation_alias=AliasChoices("EYE_VISIONARY_OFFLINE", "OFFLINE"))

    @field_validator("gps_policy")
    @classmethod
    def validate_gps_policy(cls, value: str) -> str:
        if value not in {"retain", "redact", "delete"}:
            raise ValueError("gps_policy must be retain, redact, or delete")
        return value

    @field_validator("face_vector_dimension")
    @classmethod
    def validate_supported_vector_dimension(cls, value: int) -> int:
        if value != 512:
            raise ValueError("the initial InsightFace buffalo_l schema supports a 512-dimensional vector")
        return value

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("retention_days must be positive when configured")
        return value

    def prepare_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.model_cache_root.mkdir(parents=True, exist_ok=True)

    def api_key_scopes(self) -> dict[str, set[str]]:
        """Parse ``key=scope,scope;key2=scope`` without exposing values in logs."""

        if self.api_keys is None or not self.api_keys.get_secret_value().strip():
            return {}
        parsed: dict[str, set[str]] = {}
        for entry in self.api_keys.get_secret_value().split(";"):
            if not entry.strip():
                continue
            key, separator, scopes = entry.partition("=")
            if not separator or not key.strip():
                raise ValueError("EYE_VISIONARY_API_KEYS entries must use key=scope,scope")
            parsed[key.strip()] = {scope.strip() for scope in scopes.split(",") if scope.strip()}
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()
