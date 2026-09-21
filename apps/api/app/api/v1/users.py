"""Current-user endpoints: profile read and update."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DatabaseSession
from app.schemas.users import ProfileUpdate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> UserRead:
    return user_service.to_user_read(current_user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: ProfileUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
    full_name: str | None = None,
) -> UserRead:
    # ``full_name`` arrives as an optional query parameter so the same endpoint
    # can patch the account-level field without a second schema.
    user_payload = UserUpdate(full_name=full_name) if full_name is not None else None
    return user_service.update_profile(db, current_user, payload, user_payload)
