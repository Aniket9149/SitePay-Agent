#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for client address extraction, the rate limit error and the new rate limit settings."""

from __future__ import annotations

import pytest

from app.config import load_settings
from app.errors import ConfigurationError, RateLimitedError
from app.security.client_address import UNKNOWN_ADDRESS, extract_client_address


@pytest.mark.parametrize(
    "peer,header,count,expected",
    [
        ("9.9.9.9", "1.2.3.4", 0, "9.9.9.9"),
        ("9.9.9.9", None, 1, "9.9.9.9"),
        ("9.9.9.9", "", 1, "9.9.9.9"),
        ("9.9.9.9", "1.2.3.4", 1, "1.2.3.4"),
        ("9.9.9.9", "6.6.6.6, 1.2.3.4", 1, "1.2.3.4"),
        ("9.9.9.9", "6.6.6.6, 1.2.3.4, 10.0.0.1", 2, "1.2.3.4"),
        ("9.9.9.9", "10.0.0.1", 2, "9.9.9.9"),
        ("9.9.9.9", "not-an-address", 1, "9.9.9.9"),
        ("9.9.9.9", "2001:db8::1", 1, "2001:db8::1"),
        (None, None, 0, UNKNOWN_ADDRESS),
        (None, "1.2.3.4", 1, "1.2.3.4"),
    ],
)
def test_client_address_extraction(peer: str | None, header: str | None, count: int, expected: str) -> None:
    """The header is ignored unless proxies are trusted, and a faked first entry is never used."""
    assert extract_client_address(peer, header, count) == expected


def test_rate_limited_error_shape_and_minimum_wait() -> None:
    """The error body has the standard shape, and the wait is never below one second."""
    body = RateLimitedError(0).to_response_body()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["details"] == {"retry_after_seconds": 1}


def test_new_settings_have_safe_defaults_and_are_validated() -> None:
    """Defaults match the documented values, zero proxies is allowed, bad values are refused."""
    base = {"DATABASE_URL": "sqlite://", "SECRET_KEY": "k" * 40}
    settings = load_settings(base)
    assert (settings.login_max_failures, settings.login_lockout_seconds) == (5, 900)
    assert (settings.registration_max_per_hour, settings.trusted_proxy_count) == (10, 0)
    assert load_settings({**base, "TRUSTED_PROXY_COUNT": "2"}).trusted_proxy_count == 2
    for name, bad_value in (
        ("LOGIN_MAX_FAILURES", "0"), ("LOGIN_LOCKOUT_SECONDS", "-5"),
        ("REGISTRATION_MAX_PER_HOUR", "x"), ("TRUSTED_PROXY_COUNT", "-1"),
    ):
        with pytest.raises(ConfigurationError):
            load_settings({**base, name: bad_value})
