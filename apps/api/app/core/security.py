"""Password hashing and token primitives.

Authentication is implemented once, here, and reused by every domain
(RULEBOOK rule 14: authentication must never be re-implemented per module).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import Settings

# bcrypt via passlib; a single context keeps the hash format consistent
# even if the cost factor is tuned later.
_PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp (RULEBOOK rule 120: store UTC)."""
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_CONTEXT.verify(password, password_hash)
    except ValueError:
        # Malformed hash in the database: treat as a failed login rather than
        # raising, so a corrupt record cannot lock a user out with a 500.
        return False


def create_access_token(user_id: str, settings: Settings) -> tuple[str, int, datetime]:
    """Return ``(token, expires_in_seconds, expires_at)`` for ``user_id``."""
    expires_at = utcnow() + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": user_id,
        "iat": int(utcnow().timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, settings.access_token_ttl_minutes * 60, expires_at


def decode_access_token(token: str, settings: Settings) -> str | None:
    """Return the user id encoded in ``token`` or ``None`` when it is invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Return ``(raw_token, sha256_hash, expires_at)``.

    Only the hash is persisted, so a leaked database cannot be replayed as a
    valid session. The raw value is returned to the client exactly once.
    """
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, token_hash, utcnow()


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
