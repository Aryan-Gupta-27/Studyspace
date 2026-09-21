"""Collaboration domain: groups, memberships, conversations and messages."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    Base,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
    new_uuid,
)
from app.core.security import utcnow
from app.models.identity import User


class GroupRole(enum.StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class Group(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Public groups are discoverable; every group can also be joined by code.
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    join_code: Mapped[str] = mapped_column(
        String(10), nullable=False, default=lambda: new_uuid()[:8].upper()
    )

    members: Mapped[list[GroupMember]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_groups_join_code_unique", "join_code", unique=True),)


class GroupMember(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "group_members"

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[GroupRole] = mapped_column(
        Enum(GroupRole, native_enum=False, length=16), nullable=False, default=GroupRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)
    # Drives the MVP "unread" badge: messages newer than this are unread.
    last_read_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    group: Mapped[Group] = relationship(back_populates="members")
    user: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_group_members_unique", "group_id", "user_id", unique=True),
        Index("ix_group_members_user", "user_id"),
    )


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A chat channel inside a group. Every group starts with one."""

    __tablename__ = "conversations"

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    group: Mapped[Group] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_conversations_group", "group_id"),)


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    author: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)
