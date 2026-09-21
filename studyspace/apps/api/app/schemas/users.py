"""User and profile schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ProfileRead(ORMModel):
    bio: str
    institution: str
    program: str
    academic_year: str
    skills: list[str]
    interests: list[str]


class ProfileUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=1000)
    institution: str | None = Field(default=None, max_length=200)
    program: str | None = Field(default=None, max_length=200)
    academic_year: str | None = Field(default=None, max_length=50)
    skills: list[str] | None = None
    interests: list[str] | None = None

    @field_validator("skills", "interests")
    @classmethod
    def clean_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            tag = item.strip()
            if tag and tag not in cleaned:
                cleaned.append(tag[:40])
        return cleaned[:20]


class UserBrief(ORMModel):
    id: str
    username: str
    full_name: str


class UserRead(ORMModel):
    id: str
    email: str
    username: str
    full_name: str
    created_at: datetime
    profile: ProfileRead


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
