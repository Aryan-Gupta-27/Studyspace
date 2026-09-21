"""Identity domain: users, profiles and refresh-token sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.core.security import utcnow


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    profile: Mapped[Profile] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_email_unique", "email", unique=True),
        Index("ix_users_username_unique", "username", unique=True),
    )


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    institution: Mapped[str] = mapped_column(String(200), nullable=False, default="", server_default="")
    program: Mapped[str] = mapped_column(String(200), nullable=False, default="", server_default="")
    academic_year: Mapped[str] = mapped_column(String(50), nullable=False, default="", server_default="")
    # Short, low-cardinality lists. Stored as JSON so PostgreSQL (jsonb) and
    # SQLite behave the same without a join table.
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    user: Mapped[User] = relationship(back_populates="profile")

    __table_args__ = (Index("ix_profiles_user_unique", "user_id", unique=True),)


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Persisted refresh session.

    Only the SHA-256 hash of the token is stored, so the database alone is
    never enough to impersonate a user.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_hash_unique", "token_hash", unique=True),
        Index("ix_refresh_tokens_user", "user_id"),
    )

    @property
    def is_usable(self) -> bool:
        return self.revoked_at is None and self.expires_at > utcnow()
