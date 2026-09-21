"""Authentication endpoints.

Thin by design: every rule lives in :mod:`app.services.auth_service`
(RULEBOOK rule 30).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.dependencies import DatabaseSession, SettingsDep
from app.core.rate_limit import limit_login
from app.schemas.auth import (
    AuthSession,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import ORMModel
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


class StatusResponse(ORMModel):
    status: str


@router.post("/register", response_model=AuthSession, status_code=201)
def register(
    request: Request,
    payload: RegisterRequest,
    db: DatabaseSession,
    settings: SettingsDep,
) -> AuthSession:
    limit_login(request, settings)
    user, tokens = auth_service.register(db, payload, settings)
    return AuthSession(user=user_service.to_user_read(user), tokens=tokens)


@router.post("/login", response_model=AuthSession)
def login(
    request: Request,
    payload: LoginRequest,
    db: DatabaseSession,
    settings: SettingsDep,
) -> AuthSession:
    limit_login(request, settings)
    user, tokens = auth_service.authenticate(db, payload, settings)
    return AuthSession(user=user_service.to_user_read(user), tokens=tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DatabaseSession, settings: SettingsDep) -> TokenResponse:
    return auth_service.refresh_session(db, payload.refresh_token, settings)


@router.post("/logout", response_model=StatusResponse)
def logout(payload: LogoutRequest, db: DatabaseSession) -> StatusResponse:
    auth_service.logout(db, payload.refresh_token)
    return StatusResponse(status="ok")
