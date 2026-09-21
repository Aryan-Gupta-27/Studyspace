"""Domain models.

Importing this package registers every mapped class on ``Base`` so Alembic
autogeneration and ``init_database`` see the complete schema.
"""

from app.models.collaboration import Conversation, Group, GroupMember, GroupRole, Message
from app.models.identity import Profile, RefreshToken, User
from app.models.workspace import (
    FileRecord,
    Note,
    Project,
    ProjectStatus,
    Task,
    TaskPriority,
    TaskStatus,
)

__all__ = [
    "Conversation",
    "FileRecord",
    "Group",
    "GroupMember",
    "GroupRole",
    "Message",
    "Note",
    "Profile",
    "Project",
    "ProjectStatus",
    "RefreshToken",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "User",
]
