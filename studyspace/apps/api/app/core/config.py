"""Central application configuration.

Every deployment-specific value is read from the environment so that no
credential ever lives in source control (RULEBOOK rules 12, 13, 79).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/core/config.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_DB_PATH = REPO_ROOT / "var" / "studyspace.db"
DEFAULT_STORAGE_DIR = REPO_ROOT / "var" / "storage"


class Settings(BaseSettings):
    """Runtime configuration resolved from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=(".env", str(REPO_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "StudySpace API"
    api_v1_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"
    storage_dir: Path = DEFAULT_STORAGE_DIR

    # Required: startup fails fast when the signing key is absent rather than
    # silently issuing tokens signed with a guessable default.
    jwt_secret: SecretStr = Field(..., description="HMAC key used to sign access tokens")
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14
    jwt_algorithm: str = "HS256"

    upload_max_bytes: int = 10 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:3000"]

    login_max_attempts_per_minute: int = 10
    upload_max_attempts_per_minute: int = 30
    write_max_attempts_per_minute: int = 120

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor so configuration is parsed only once."""
    # ``jwt_secret`` has no default on purpose: startup must fail rather than
    # sign tokens with a guessable key. It is supplied by the environment,
    # which is invisible to the type checker.
    return Settings()  # type: ignore[call-arg]
