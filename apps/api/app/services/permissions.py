"""Central authorisation rules.

Every protected operation funnels through this module so permission logic is
defined once and never re-implemented per route or per domain (RULEBOOK rules
14, 15, 98). The frontend is never treated as a security boundary.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models.collaboration import Conversation, Group, GroupMember, GroupRole, Message
from app.models.identity import User
from app.models.workspace import Note, Project, Task

#: Roles allowed to change group settings, members and shared content.
MANAGER_ROLES = (GroupRole.OWNER, GroupRole.ADMIN)


def get_group(db: Session, group_id: str) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        # A non-member must not be able to distinguish "missing" from
        # "private", so the message stays generic.
        raise NotFoundError("We couldn't find that group.")
    return group


def require_membership(db: Session, group_id: str, user: User) -> GroupMember:
    """Return the caller's membership or fail with 403/404."""
    get_group(db, group_id)
    member = db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    )
    if member is None:
        raise ForbiddenError("You need to be a member of this group to do that.")
    return member


def require_manager(db: Session, group_id: str, user: User) -> GroupMember:
    member = require_membership(db, group_id, user)
    if member.role not in MANAGER_ROLES:
        raise ForbiddenError("Only group owners and admins can do that.")
    return member


def require_owner(db: Session, group_id: str, user: User) -> GroupMember:
    member = require_membership(db, group_id, user)
    if member.role is not GroupRole.OWNER:
        raise ForbiddenError("Only the group owner can do that.")
    return member


def is_manager(member: GroupMember) -> bool:
    return member.role in MANAGER_ROLES


def require_conversation_access(db: Session, conversation_id: str, user: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("We couldn't find that conversation.")
    require_membership(db, conversation.group_id, user)
    return conversation


def can_edit_message(message: Message, user: User, member: GroupMember) -> bool:
    return message.author_id == user.id or is_manager(member)


def require_note_access(db: Session, note_id: str, user: User) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise NotFoundError("We couldn't find that note.")
    if note.group_id is None:
        if note.owner_id != user.id:
            raise ForbiddenError("That note is private.")
        return note
    require_membership(db, note.group_id, user)
    return note


def require_note_edit_access(db: Session, note_id: str, user: User) -> Note:
    """Group notes are collaborative: any member may edit them.

    A shared note is study material for the whole group, so requiring authorship
    would block the collaboration the product is built around. Private notes
    stay with their owner.
    """
    return require_note_access(db, note_id, user)


def require_note_delete_access(db: Session, note_id: str, user: User) -> Note:
    """Deletion is destructive, so it is limited to the author or a manager."""
    note = require_note_access(db, note_id, user)
    if note.group_id is None:
        return note
    member = require_membership(db, note.group_id, user)
    if note.owner_id != user.id and not is_manager(member):
        raise ForbiddenError("Only the note author or a group admin can delete this note.")
    return note


def require_project_access(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("We couldn't find that project.")
    require_membership(db, project.group_id, user)
    return project


def require_task_access(db: Session, task_id: str, user: User) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError("We couldn't find that task.")
    require_project_access(db, task.project_id, user)
    return task


def count_group_members(db: Session, group_id: str) -> int:
    return int(
        db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group_id)) or 0
    )
