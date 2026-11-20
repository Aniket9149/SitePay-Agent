#Owner::ANIKET::ANHOTRA = MR.Panda
"""Creates and checks signed login tokens (JSON Web Tokens, algorithm HS256).

Access tokens are short lived. Refresh tokens carry a unique token identifier so the
server can revoke them. The algorithm is fixed, never read from the token itself.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.errors import AuthenticationError

TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
REQUIRED_CLAIMS = ["exp", "iat", "sub", "jti", "type"]


@dataclass(frozen=True)
class TokenClaims:
    """The verified contents of a token."""

    user_id: str
    token_type: str
    token_id: str
    issued_at: datetime
    expires_at: datetime


def create_token(
    *,
    user_id: str,
    token_type: str,
    secret_key: str,
    lifetime: timedelta,
    token_id: str | None = None,
    issued_at: datetime | None = None,
) -> str:
    """Create a signed token of the given type that expires after the lifetime.

    A random token identifier is generated unless one is supplied.
    """
    issue_time = issued_at or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": token_type,
        "jti": token_id or str(uuid.uuid4()),
        "iat": int(issue_time.timestamp()),
        "exp": int((issue_time + lifetime).timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=TOKEN_ALGORITHM)


def decode_token(token: str, secret_key: str, expected_type: str) -> TokenClaims:
    """Verify signature, expiry and type, then return the claims.

    Raises AuthenticationError with a generic message for any problem.
    """
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[TOKEN_ALGORITHM],
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as error:
        raise AuthenticationError("The login token is invalid or has expired.") from error
    if payload.get("type") != expected_type:
        raise AuthenticationError("The login token is invalid or has expired.")
    return TokenClaims(
        user_id=str(payload["sub"]),
        token_type=str(payload["type"]),
        token_id=str(payload["jti"]),
        issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
        expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
    )
