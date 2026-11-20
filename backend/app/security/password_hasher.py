#Owner::ANIKET::ANHOTRA = MR.Panda
"""Password hashing with scrypt from the Python standard library.

Stored format: scrypt$cost$block_size$parallelism$salt$hash, with salt and hash in base64.
The parameters are stored with each hash so they can be raised later without breaking
old passwords. Comparison is constant time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import unicodedata

SCHEME_NAME = "scrypt"
SCRYPT_COST = 2**15
SCRYPT_BLOCK_SIZE = 8
SCRYPT_PARALLELISM = 1
SALT_BYTE_COUNT = 16
DERIVED_KEY_BYTE_COUNT = 32
MAXIMUM_MEMORY_BYTES = 128 * 1024 * 1024
MAXIMUM_PASSWORD_LENGTH = 128
# Upper bound on stored cost, so a tampered row cannot force huge memory use.
MAXIMUM_ACCEPTED_COST = 2**20

_dummy_hash_cache: list[str] = []


def _normalise_password(password: str) -> bytes:
    """Normalise the password text to UTF-8 bytes using Unicode NFKC.

    This makes visually identical passwords hash the same on every device.
    """
    return unicodedata.normalize("NFKC", password).encode("utf-8")


def _derive_key(password: str, salt: bytes, cost: int, block_size: int, parallelism: int) -> bytes:
    """Run scrypt with the given parameters and return the derived key bytes.

    A single place for the call keeps hashing and verifying identical.
    """
    return hashlib.scrypt(
        _normalise_password(password),
        salt=salt,
        n=cost,
        r=block_size,
        p=parallelism,
        maxmem=MAXIMUM_MEMORY_BYTES,
        dklen=DERIVED_KEY_BYTE_COUNT,
    )


def hash_password(password: str) -> str:
    """Hash a password with a fresh random salt and return the storable text.

    Raises ValueError for an empty password or one over the maximum length.
    """
    if password == "" or len(password) > MAXIMUM_PASSWORD_LENGTH:
        raise ValueError("Password length is outside the allowed range.")
    salt = secrets.token_bytes(SALT_BYTE_COUNT)
    derived_key = _derive_key(
        password, salt, SCRYPT_COST, SCRYPT_BLOCK_SIZE, SCRYPT_PARALLELISM
    )
    return "$".join(
        [
            SCHEME_NAME,
            str(SCRYPT_COST),
            str(SCRYPT_BLOCK_SIZE),
            str(SCRYPT_PARALLELISM),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived_key).decode("ascii"),
        ]
    )


def _parse_stored_hash(stored_hash: str) -> tuple[int, int, int, bytes, bytes] | None:
    """Split a stored hash into its parts, or return None if it is malformed.

    Never raises, so a corrupted row simply fails to verify.
    """
    parts = stored_hash.split("$")
    if len(parts) != 6 or parts[0] != SCHEME_NAME:
        return None
    try:
        cost, block_size, parallelism = int(parts[1]), int(parts[2]), int(parts[3])
        salt = base64.b64decode(parts[4], validate=True)
        expected_key = base64.b64decode(parts[5], validate=True)
    except ValueError:
        return None
    cost_is_power_of_two = cost > 1 and (cost & (cost - 1)) == 0
    if not cost_is_power_of_two or cost > MAXIMUM_ACCEPTED_COST:
        return None
    if block_size <= 0 or parallelism <= 0 or len(salt) == 0 or len(expected_key) == 0:
        return None
    return cost, block_size, parallelism, salt, expected_key


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True only when the password matches the stored hash.

    Malformed hashes and over-long passwords return False instead of raising.
    """
    parsed = _parse_stored_hash(stored_hash)
    if parsed is None or len(password) > MAXIMUM_PASSWORD_LENGTH:
        return False
    cost, block_size, parallelism, salt, expected_key = parsed
    try:
        actual_key = _derive_key(password, salt, cost, block_size, parallelism)
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(actual_key, expected_key)


def password_needs_rehash(stored_hash: str) -> bool:
    """Return True when the stored hash uses weaker parameters than today's.

    The login flow can then upgrade the hash after a successful login.
    """
    parsed = _parse_stored_hash(stored_hash)
    if parsed is None:
        return True
    cost, block_size, parallelism, _salt, _key = parsed
    return (cost, block_size, parallelism) != (
        SCRYPT_COST,
        SCRYPT_BLOCK_SIZE,
        SCRYPT_PARALLELISM,
    )


def verify_against_dummy_hash(password: str) -> None:
    """Spend the same time as a real check when the email is unknown.

    This stops an attacker learning which emails exist by measuring response time.
    """
    if not _dummy_hash_cache:
        _dummy_hash_cache.append(hash_password("dummy-password-for-timing-only"))
    verify_password(password, _dummy_hash_cache[0])
