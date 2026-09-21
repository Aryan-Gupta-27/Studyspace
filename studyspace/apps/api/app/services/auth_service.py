"""Registration, login and session management.

Rules implemented here (RULEBOOK rules 14, 56, 98):
* one central authentication path reused by every domain;
* failed logins are indistinguishable (no account enumeration);
* refresh tokens are stored only as hashes and are rotated on every use.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, InvalidCredentialsError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    utcnow,
    verify_password,
)
from app.models.identity import Profile, RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def _find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def _username_taken(db: Session, username: str) -> bool:
    return (
        db.scalar(select(func.count()).select_from(User).where(User.username == username)) or 0
    ) > 0


def issue_tokens(db: Session, user: User, settings: Settings) -> TokenResponse:
    """Mint an access/refresh pair and persist the refresh session."""
    access_token, expires_in, _ = create_access_token(user.id, settings)
    raw_refresh, refresh_hash, created_at = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            created_at=created_at,
            expires_at=created_at + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.flush()
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=expires_in,
    )


def register(db: Session, payload: RegisterRequest, settings: Settings) -> tuple[User, TokenResponse]:
    email = str(payload.email).strip().lower()
    if _find_by_email(db, email) is not None:
        raise ConflictError("An account with that email already exists.")
    if _username_taken(db, payload.username):
        raise ConflictError("That username is already taken.")

    user = User(
        email=email,
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    # Profile is created together with the account so /users/me never has to
    # handle a missing row; the two writes are one atomic step.
    db.add(Profile(user_id=user.id))
    tokens = issue_tokens(db, user, settings)
    db.commit()
    db.refresh(user)
    return user, tokens


def authenticate(db: Session, payload: LoginRequest, settings: Settings) -> tuple[User, TokenResponse]:
    user = _find_by_email(db, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        # Same response whether the account or the password was wrong.
        raise InvalidCredentialsError()
    if not user.is_active:
        raise UnauthorizedError("This account is no longer active.")
    tokens = issue_tokens(db, user, settings)
    db.commit()
    return user, tokens


def refresh_session(db: Session, raw_token: str, settings: Settings) -> TokenResponse:
    token_hash = hash_refresh_token(raw_token)
    session = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if session is None or not session.is_usable:
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    # Rotation: the presented token is single-use, so a stolen refresh token
    # cannot be replayed after the legitimate client rotates it.
    session.revoked_at = utcnow()
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        db.commit()
        raise UnauthorizedError("Your session has expired. Please sign in again.")
    tokens = issue_tokens(db, user, settings)
    db.commit()
    return tokens


def logout(db: Session, raw_token: str) -> None:
    """Revoke one session. Unknown or expired tokens are a no-op."""
    session = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


def revoke_user_sessions(db: Session, user_id: str) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": utcnow()})
    db.commit()
