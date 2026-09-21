"""Profile reads and updates."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.identity import User
from app.schemas.users import ProfileRead, ProfileUpdate, UserRead, UserUpdate

# Guard rails on profile lists: bounded so a client cannot inflate storage.
MAX_TAGS = 20


def to_user_read(user: User) -> UserRead:
    profile = user.profile
    return UserRead(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        created_at=user.created_at,
        profile=ProfileRead(
            bio=profile.bio if profile else "",
            institution=profile.institution if profile else "",
            program=profile.program if profile else "",
            academic_year=profile.academic_year if profile else "",
            skills=list(profile.skills) if profile and profile.skills else [],
            interests=list(profile.interests) if profile and profile.interests else [],
        ),
    )


def update_profile(db: Session, user: User, payload: ProfileUpdate, user_payload: UserUpdate | None = None) -> UserRead:
    if user_payload is not None and user_payload.full_name is not None:
        user.full_name = user_payload.full_name.strip()

    profile = user.profile
    if profile is None:  # pragma: no cover - accounts always get a profile
        from app.models.identity import Profile

        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()

    # Only fields explicitly present are touched, so the endpoint works as PATCH.
    for field in ("bio", "institution", "program", "academic_year"):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value.strip())
    if payload.skills is not None:
        profile.skills = payload.skills[:MAX_TAGS]
    if payload.interests is not None:
        profile.interests = payload.interests[:MAX_TAGS]

    db.commit()
    db.refresh(user)
    return to_user_read(user)
