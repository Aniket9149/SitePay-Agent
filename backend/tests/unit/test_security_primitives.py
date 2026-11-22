#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for password hashing, tokens, permissions and the audit hash chain."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import jwt
import pytest

from app.errors import AuthenticationError, DomainValidationError
from app.security import password_hasher
from app.security.audit_hash import (
    GENESIS_HASH,
    canonical_timestamp,
    compute_entry_hash,
    find_first_broken_position,
    make_json_safe,
)
from app.security.permissions import (
    Permission,
    Role,
    parse_role,
    role_has_permission,
    would_leave_organization_without_owner,
)
from app.security.token_service import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_token,
    decode_token,
)

SECRET = "s" * 40


def test_password_round_trip_and_wrong_password() -> None:
    """The right password verifies and a wrong one does not."""
    stored = password_hasher.hash_password("correct horse 42")
    assert password_hasher.verify_password("correct horse 42", stored) is True
    assert password_hasher.verify_password("correct horse 43", stored) is False


def test_same_password_gets_different_salts() -> None:
    """Two hashes of one password differ because each has a random salt."""
    first = password_hasher.hash_password("same-password-1")
    second = password_hasher.hash_password("same-password-1")
    assert first != second


def test_unicode_normalisation_makes_equivalent_passwords_match() -> None:
    """The same visible password typed in two Unicode forms verifies."""
    composed = "café-pass-1"
    decomposed = "café-pass-1"
    stored = password_hasher.hash_password(composed)
    assert password_hasher.verify_password(decomposed, stored) is True


@pytest.mark.parametrize("bad_password", ["", "x" * 129])
def test_hashing_rejects_empty_and_overlong(bad_password: str) -> None:
    """Empty and over-long passwords cannot be hashed."""
    with pytest.raises(ValueError):
        password_hasher.hash_password(bad_password)


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "plain",
        "scrypt$1$2$3",
        "scrypt$abc$8$1$AAAA$AAAA",
        "bcrypt$16384$8$1$AAAA$AAAA",
        "scrypt$3$8$1$AAAA$AAAA",
        "scrypt$2147483648$8$1$AAAA$AAAA",
        "scrypt$32768$8$1$!!!!$AAAA",
    ],
)
def test_malformed_hashes_fail_without_raising(malformed: str) -> None:
    """A corrupted or tampered stored hash verifies as False, never crashes."""
    assert password_hasher.verify_password("anything-1", malformed) is False


def test_overlong_password_does_not_verify() -> None:
    """Very long input is rejected before any expensive work."""
    stored = password_hasher.hash_password("normal-password-1")
    assert password_hasher.verify_password("x" * 5000, stored) is False


def test_rehash_detection() -> None:
    """Hashes with current parameters are fine, weaker or broken ones need a rehash."""
    current = password_hasher.hash_password("normal-password-1")
    assert password_hasher.password_needs_rehash(current) is False
    weaker = current.replace(f"${password_hasher.SCRYPT_COST}$", "$16384$", 1)
    assert password_hasher.password_needs_rehash(weaker) is True
    assert password_hasher.password_needs_rehash("garbage") is True


def test_dummy_verification_runs_without_error() -> None:
    """The timing equaliser for unknown emails runs and returns nothing."""
    assert password_hasher.verify_against_dummy_hash("whatever-1") is None


def make_access(**overrides: object) -> str:
    """Create an access token with test defaults and optional overrides.

    Keeps the token tests short.
    """
    arguments: dict[str, object] = {
        "user_id": "user-1",
        "token_type": ACCESS_TOKEN_TYPE,
        "secret_key": SECRET,
        "lifetime": timedelta(minutes=30),
    }
    arguments.update(overrides)
    return create_token(**arguments)  # type: ignore[arg-type]


def test_token_round_trip() -> None:
    """A fresh token decodes back to the same user and type."""
    claims = decode_token(make_access(), SECRET, ACCESS_TOKEN_TYPE)
    assert claims.user_id == "user-1"
    assert claims.token_type == ACCESS_TOKEN_TYPE
    assert claims.expires_at > claims.issued_at


def test_expired_token_is_rejected() -> None:
    """A token whose lifetime has passed does not decode."""
    old_token = make_access(
        issued_at=datetime.now(UTC) - timedelta(hours=2), lifetime=timedelta(minutes=1)
    )
    with pytest.raises(AuthenticationError):
        decode_token(old_token, SECRET, ACCESS_TOKEN_TYPE)


def test_wrong_secret_and_tampering_are_rejected() -> None:
    """A token signed with another key, or edited, is rejected."""
    token = make_access()
    with pytest.raises(AuthenticationError):
        decode_token(token, "o" * 40, ACCESS_TOKEN_TYPE)
    with pytest.raises(AuthenticationError):
        decode_token(
            token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB"), SECRET, ACCESS_TOKEN_TYPE
        )


def test_token_type_confusion_is_rejected() -> None:
    """A refresh token cannot be used as an access token, or the reverse."""
    refresh_token = make_access(token_type=REFRESH_TOKEN_TYPE)
    with pytest.raises(AuthenticationError):
        decode_token(refresh_token, SECRET, ACCESS_TOKEN_TYPE)
    assert decode_token(refresh_token, SECRET, REFRESH_TOKEN_TYPE).token_type == REFRESH_TOKEN_TYPE


def test_unsigned_none_algorithm_token_is_rejected() -> None:
    """A token that claims no signature at all is refused."""
    now = int(datetime.now(UTC).timestamp())
    payload = {"sub": "u", "type": ACCESS_TOKEN_TYPE, "jti": "j", "iat": now, "exp": now + 600}
    forged = jwt.encode(payload, key=None, algorithm="none")
    with pytest.raises(AuthenticationError):
        decode_token(forged, SECRET, ACCESS_TOKEN_TYPE)


def test_token_missing_required_claim_is_rejected() -> None:
    """A correctly signed token without a required claim is refused."""
    now = int(datetime.now(UTC).timestamp())
    incomplete = jwt.encode({"sub": "u", "iat": now, "exp": now + 600}, SECRET, algorithm="HS256")
    with pytest.raises(AuthenticationError):
        decode_token(incomplete, SECRET, ACCESS_TOKEN_TYPE)


def test_owner_has_every_permission_and_worker_only_reads() -> None:
    """The owner can do everything, a worker cannot change anything."""
    assert all(role_has_permission(Role.OWNER, permission) for permission in Permission)
    assert role_has_permission(Role.WORKER, Permission.PROJECT_READ) is True
    assert role_has_permission(Role.WORKER, Permission.PROJECT_UPDATE) is False
    assert role_has_permission(Role.ENGINEER, Permission.SITE_MANAGE) is True
    assert role_has_permission(Role.ENGINEER, Permission.PROJECT_CREATE) is False
    assert role_has_permission(Role.ACCOUNTS, Permission.MEMBER_MANAGE) is False
    assert role_has_permission(Role.MANAGER, Permission.MEMBER_MANAGE) is False


def test_unknown_role_text_has_no_permissions() -> None:
    """Unknown roles are denied, and parsing them raises."""
    assert role_has_permission("superuser", Permission.PROJECT_READ) is False
    with pytest.raises(DomainValidationError):
        parse_role("superuser")
    assert parse_role("manager") is Role.MANAGER


def test_last_owner_protection() -> None:
    """Demoting or removing the only owner is flagged, other changes are not."""
    roles = {"m1": Role.OWNER, "m2": Role.ENGINEER}
    assert would_leave_organization_without_owner(roles, "m1", Role.MANAGER) is True
    assert would_leave_organization_without_owner(roles, "m1", None) is True
    assert would_leave_organization_without_owner(roles, "m2", None) is False
    assert would_leave_organization_without_owner(roles, "m2", Role.OWNER) is False
    two_owners = {"m1": Role.OWNER, "m2": Role.OWNER}
    assert would_leave_organization_without_owner(two_owners, "m1", Role.WORKER) is False


def build_chain(count: int) -> list[dict[str, object]]:
    """Build a valid audit chain of the given length for tests.

    Each entry is hashed with the one before it.
    """
    entries: list[dict[str, object]] = []
    previous_hash = GENESIS_HASH
    for position in range(1, count + 1):
        entry: dict[str, object] = {
            "chain_scope": "org-1",
            "chain_position": position,
            "organization_id": "org-1",
            "actor_user_id": "user-1",
            "action": "project.created",
            "target_type": "project",
            "target_id": f"p{position}",
            "value_before": None,
            "value_after": {"name": f"Project {position}"},
            "reason": None,
            "created_at": "2026-11-20T10:00:00.000000Z",
            "previous_entry_hash": previous_hash,
        }
        entry["entry_hash"] = compute_entry_hash(previous_hash, entry)
        previous_hash = str(entry["entry_hash"])
        entries.append(entry)
    return entries


def test_intact_chain_has_no_broken_position() -> None:
    """A correctly built chain, and an empty one, pass the check."""
    assert find_first_broken_position(build_chain(5)) is None
    assert find_first_broken_position([]) is None


def test_edited_entry_is_detected() -> None:
    """Changing any hashed field of entry 3 is reported at position 3."""
    chain = build_chain(5)
    chain[2]["value_after"] = {"name": "Tampered"}
    assert find_first_broken_position(chain) == 3


def test_deleted_entry_is_detected() -> None:
    """Removing entry 2 breaks the chain at the position that now follows the gap."""
    chain = build_chain(4)
    del chain[1]
    assert find_first_broken_position(chain) == 2


def test_reordered_entries_are_detected() -> None:
    """Swapping two entries is reported."""
    chain = build_chain(4)
    chain[1], chain[2] = chain[2], chain[1]
    assert find_first_broken_position(chain) == 2


def test_hash_ignores_key_order_but_not_values() -> None:
    """The hash depends on content, not on the order fields were written."""
    entry = build_chain(1)[0]
    shuffled = dict(reversed(list(entry.items())))
    assert compute_entry_hash(GENESIS_HASH, entry) == compute_entry_hash(GENESIS_HASH, shuffled)
    changed = dict(entry, action="project.deleted")
    assert compute_entry_hash(GENESIS_HASH, entry) != compute_entry_hash(GENESIS_HASH, changed)


def test_json_safe_conversion_keeps_money_exact() -> None:
    """Decimals stay exact as text, and nested values convert."""
    converted = make_json_safe({"amount": Decimal("1250000.50"), "roles": {Role.OWNER}, "n": 3})
    assert converted == {"amount": "1250000.50", "roles": ["owner"], "n": 3}


def test_canonical_timestamp_treats_naive_as_utc() -> None:
    """Naive and aware versions of the same UTC moment give identical text."""
    naive = datetime(2026, 11, 20, 10, 0, 0, 5)
    aware = datetime(2026, 11, 20, 10, 0, 0, 5, tzinfo=UTC)
    assert canonical_timestamp(naive) == canonical_timestamp(aware) == "2026-11-20T10:00:00.000005Z"
