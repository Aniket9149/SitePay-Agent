#Owner::ANIKET::ANHOTRA = MR.Panda
"""Reads all settings from environment variables and refuses unsafe values.

No secret ever lives in code. Staging and production must use PostgreSQL and a
long secret key. Settings are an immutable object so they cannot change at runtime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from app.errors import ConfigurationError

ALLOWED_ENVIRONMENTS = ("development", "staging", "production")
MINIMUM_SECRET_KEY_LENGTH = 32
PLACEHOLDER_SECRET_PREFIX = "replace-with"


@dataclass(frozen=True)
class Settings:
    """All runtime settings for the backend, read once at start."""

    application_environment: str
    database_url: str
    secret_key: str
    access_token_lifetime_minutes: int
    refresh_token_lifetime_days: int
    feature_flags_raw: str
    log_level: str


def _read_positive_integer(source: Mapping[str, str], name: str, default: int) -> int:
    """Read a positive whole number setting, using the default when unset.

    Raises ConfigurationError for text that is not a positive integer.
    """
    raw_value = source.get(name, "").strip()
    if raw_value == "":
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a whole number.") from error
    if parsed_value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return parsed_value


def _validate_secret_key(secret_key: str) -> None:
    """Reject missing, placeholder or short secret keys.

    The key signs login tokens, so a weak key would let anyone forge them.
    """
    if secret_key == "" or secret_key.startswith(PLACEHOLDER_SECRET_PREFIX):
        raise ConfigurationError("SECRET_KEY must be set to a real random value.")
    if len(secret_key) < MINIMUM_SECRET_KEY_LENGTH:
        raise ConfigurationError(
            f"SECRET_KEY must be at least {MINIMUM_SECRET_KEY_LENGTH} characters long."
        )


def load_settings(environment: Mapping[str, str] | None = None) -> Settings:
    """Build validated Settings from the given mapping or the process environment.

    Raises ConfigurationError on any missing or unsafe value.
    """
    source: Mapping[str, str] = os.environ if environment is None else environment
    application_environment = source.get("APPLICATION_ENVIRONMENT", "development").strip()
    if application_environment not in ALLOWED_ENVIRONMENTS:
        raise ConfigurationError(
            "APPLICATION_ENVIRONMENT must be one of: " + ", ".join(ALLOWED_ENVIRONMENTS) + "."
        )
    database_url = source.get("DATABASE_URL", "").strip()
    if database_url == "":
        raise ConfigurationError("DATABASE_URL must be set.")
    if application_environment != "development" and database_url.startswith("sqlite"):
        raise ConfigurationError("Staging and production must use PostgreSQL, not SQLite.")
    secret_key = source.get("SECRET_KEY", "")
    _validate_secret_key(secret_key)
    return Settings(
        application_environment=application_environment,
        database_url=database_url,
        secret_key=secret_key,
        access_token_lifetime_minutes=_read_positive_integer(
            source, "ACCESS_TOKEN_LIFETIME_MINUTES", 30
        ),
        refresh_token_lifetime_days=_read_positive_integer(
            source, "REFRESH_TOKEN_LIFETIME_DAYS", 7
        ),
        feature_flags_raw=source.get("FEATURE_FLAGS", "").strip(),
        log_level=source.get("LOG_LEVEL", "INFO").strip().upper(),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process wide settings, loaded once from the environment.

    Tests that need different values call load_settings directly instead.
    """
    return load_settings()
