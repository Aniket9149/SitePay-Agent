#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for settings loading, error bodies, feature flags and logging."""

from __future__ import annotations

import json
import logging

import pytest

from app.config import load_settings
from app.errors import ConfigurationError, NotFoundError, SitePayError
from app.feature_flags import FeatureFlags
from app.logging_setup import JsonLogFormatter, configure_logging

GOOD_SECRET = "x" * 40


def good_environment(**overrides: str) -> dict[str, str]:
    """Return a valid settings mapping with optional overrides.

    Keeps each test focused on the one value it changes.
    """
    environment = {
        "DATABASE_URL": "sqlite:///./test.sqlite3",
        "SECRET_KEY": GOOD_SECRET,
    }
    environment.update(overrides)
    return environment


def test_defaults_are_applied() -> None:
    """Unset optional values fall back to safe defaults."""
    settings = load_settings(good_environment())
    assert settings.application_environment == "development"
    assert settings.access_token_lifetime_minutes == 30
    assert settings.refresh_token_lifetime_days == 7
    assert settings.log_level == "INFO"


def test_missing_database_url_is_rejected() -> None:
    """The database url is required."""
    with pytest.raises(ConfigurationError):
        load_settings({"SECRET_KEY": GOOD_SECRET})


@pytest.mark.parametrize("bad_secret", ["", "short", "replace-with-a-long-random-value" + "y" * 20])
def test_missing_short_or_placeholder_secret_is_rejected(bad_secret: str) -> None:
    """Empty, short and placeholder secrets must never be accepted."""
    with pytest.raises(ConfigurationError):
        load_settings(good_environment(SECRET_KEY=bad_secret))


def test_unknown_environment_is_rejected() -> None:
    """Only development, staging and production are valid."""
    with pytest.raises(ConfigurationError):
        load_settings(good_environment(APPLICATION_ENVIRONMENT="testing"))


@pytest.mark.parametrize("environment_name", ["staging", "production"])
def test_sqlite_is_rejected_outside_development(environment_name: str) -> None:
    """Staging and production require PostgreSQL."""
    with pytest.raises(ConfigurationError):
        load_settings(good_environment(APPLICATION_ENVIRONMENT=environment_name))


def test_postgresql_is_accepted_in_production() -> None:
    """A PostgreSQL url is valid in production."""
    settings = load_settings(
        good_environment(
            APPLICATION_ENVIRONMENT="production", DATABASE_URL="postgresql://u:p@db/sitepay"
        )
    )
    assert settings.application_environment == "production"


@pytest.mark.parametrize("bad_value", ["abc", "0", "-5", "1.5"])
def test_bad_token_lifetimes_are_rejected(bad_value: str) -> None:
    """Lifetimes must be positive whole numbers."""
    with pytest.raises(ConfigurationError):
        load_settings(good_environment(ACCESS_TOKEN_LIFETIME_MINUTES=bad_value))


def test_settings_are_immutable() -> None:
    """Settings cannot be changed after loading."""
    settings = load_settings(good_environment())
    with pytest.raises(AttributeError):
        settings.secret_key = "other"  # type: ignore[misc]


def test_error_body_shape_is_stable() -> None:
    """Every error renders as an error object with a code and message."""
    body = NotFoundError("Project not found.", details={"id": "1"}).to_response_body()
    assert body == {
        "error": {"code": "not_found", "message": "Project not found.", "details": {"id": "1"}}
    }
    assert "details" not in SitePayError("x").to_response_body()["error"]


def test_feature_flags_parse_and_query() -> None:
    """Known flags parse from text, ignoring blanks and spaces."""
    flags = FeatureFlags.from_text(" face_blur , ,ai_extraction")
    assert flags.enabled_names() == ["ai_extraction", "face_blur"]
    assert flags.is_enabled("face_blur") is True
    assert flags.is_enabled("password_reset") is False


def test_unknown_feature_flag_is_an_error() -> None:
    """A typo in a flag name must fail loudly, not silently stay off."""
    with pytest.raises(ConfigurationError):
        FeatureFlags.from_text("face_blurr")
    with pytest.raises(ConfigurationError):
        FeatureFlags.from_text("").is_enabled("nonexistent")


def test_json_log_formatter_outputs_valid_json() -> None:
    """Each log line is a JSON object with the expected keys."""
    record = logging.LogRecord("sitepay.test", logging.WARNING, "f.py", 1, "hello %s", ("world",), None)
    parsed = json.loads(JsonLogFormatter().format(record))
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "sitepay.test"


def test_configure_logging_is_idempotent() -> None:
    """Calling configure twice leaves one SitePay handler on the root logger."""
    configure_logging("debug")
    configure_logging("not-a-level")
    root_logger = logging.getLogger()
    handlers = [h for h in root_logger.handlers if getattr(h, "_sitepay_handler", False)]
    assert len(handlers) == 1
    assert root_logger.level == logging.INFO
