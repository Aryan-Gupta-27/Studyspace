"""Workspace domain: notes, file records, projects and tasks.

Notes and files are either personal (``group_id`` is NULL) or shared with a
group; projects and tasks always belong to a group. Data ownership is
explicit in the schema so authorisation never has to guess (RULEBOOK rule 71).
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.identity import User


class ProjectStatus(enum.StrEnum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"


class TaskStatus(enum.StrEnum):
    """The four board columns required by milestone 6."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"


class TaskPriority(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Note(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # NULL means a private note; otherwise the note is shared with the group.
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )

    owner: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_notes_owner", "owner_id"),
        Index("ix_notes_group", "group_id"),
    )


class FileRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata only; the bytes live in the storage backend (RULEBOOK rule 46)."""

    __tablename__ = "files"

    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False, default="application/octet-stream")
    size: Mapped[int] = mapped_column(nullable=False)
    # Server-generated opaque key. Never derived from the client filename.
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)

    owner: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_files_owner", "owner_id"),
        Index("ix_files_group", "group_id"),
        Index("ix_files_storage_key_unique", "storage_key", unique=True),
    )


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=16),
        nullable=False,
        default=ProjectStatus.PLANNING,
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[created_by_id])

    tasks: Mapped[list[Task]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_projects_group", "group_id"),)


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=16), nullable=False, default=TaskStatus.TODO
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=16), nullable=False, default=TaskPriority.MEDIUM
    )
    # Monotonically increasing within a column so the board keeps a stable order.
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    assignee_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[assignee_id])
    created_by: Mapped[User] = relationship(lazy="joined", foreign_keys=[created_by_id])

    __table_args__ = (Index("ix_tasks_project_status", "project_id", "status"),)
