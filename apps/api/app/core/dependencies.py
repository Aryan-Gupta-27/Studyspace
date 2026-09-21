"""Shared FastAPI dependencies: database session and authenticated identity."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.models.identity import User
from app.schemas.common import PageParams

DatabaseSession = Annotated[Session, Depends(get_db)]


def pagination(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> PageParams:
    """Shared, bounded pagination window so no endpoint can dump the table."""
    return PageParams(limit=limit, offset=offset)


Pagination = Annotated[PageParams, Depends(pagination)]


def get_settings_dependency() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def get_current_user(
    request: Request,
    db: DatabaseSession,
    settings: SettingsDep,
) -> User:
    """Resolve the caller from the ``Authorization`` header.

    Identity always comes from a verified token; nothing about the user is
    trusted from the request body or query string (RULEBOOK rules 15, 98).
    """
    token = bearer_token(request)
    if token is None:
        raise UnauthorizedError("Please sign in to continue.")

    user_id = decode_access_token(token, settings)
    if user_id is None:
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Your session is no longer valid. Please sign in again.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
