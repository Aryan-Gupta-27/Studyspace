"""Authentication request and response schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.users import UserRead

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,32}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=32)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalise_username(cls, value: str) -> str:
        username = value.strip().lower()
        if not USERNAME_PATTERN.match(username):
            raise ValueError("Use 3-32 characters: lowercase letters, numbers or underscores.")
        return username

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Choose a password that is not only spaces.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthSession(BaseModel):
    """Everything the web client needs immediately after signing in."""

    user: UserRead
    tokens: TokenResponse


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class MessageResponse(BaseModel):
    message: str
