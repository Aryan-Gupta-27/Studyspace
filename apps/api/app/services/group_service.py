"""Group lifecycle: create, discover, join, leave, update, delete.

Creating a group, adding its owner and opening its first conversation is one
atomic operation, so a group can never exist without somewhere to talk
(RULEBOOK rule 27).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import paginate
from app.core.errors import ConflictError, ForbiddenError, ValidationError
from app.models.collaboration import Conversation, Group, GroupMember, GroupRole, Message
from app.models.identity import User
from app.models.workspace import FileRecord
from app.schemas.common import Page, PageParams
from app.schemas.groups import (
    GroupCreate,
    GroupMemberRead,
    GroupRead,
    GroupSummary,
    GroupUpdate,
)
from app.services.permissions import (
    count_group_members,
    get_group,
    require_manager,
    require_membership,
    require_owner,
)
from app.services.storage import get_storage


def member_counts(db: Session, group_ids: list[str]) -> dict[str, int]:
    if not group_ids:
        return {}
    rows = db.execute(
        select(GroupMember.group_id, func.count(GroupMember.id))
        .where(GroupMember.group_id.in_(group_ids))
        .group_by(GroupMember.group_id)
    ).all()
    return {group_id: int(count) for group_id, count in rows}


def unread_counts(db: Session, user_id: str) -> dict[str, int]:
    """Unread messages per group, computed in a single grouped query.

    A message counts as unread when someone else wrote it after the caller's
    ``last_read_at`` watermark for that group.
    """
    rows = db.execute(
        select(Conversation.group_id, func.count(Message.id))
        .join(Message, Message.conversation_id == Conversation.id)
        .join(
            GroupMember,
            (GroupMember.group_id == Conversation.group_id) & (GroupMember.user_id == user_id),
        )
        .where(Message.author_id != user_id)
        .where(
            (GroupMember.last_read_at.is_(None)) | (Message.created_at > GroupMember.last_read_at)
        )
        .group_by(Conversation.group_id)
    ).all()
    return {group_id: int(count) for group_id, count in rows}


def to_group_read(
    db: Session,
    group: Group,
    member: GroupMember,
    member_count: int | None = None,
    unread_count: int | None = None,
) -> GroupRead:
    return GroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        is_public=group.is_public,
        join_code=group.join_code,
        created_at=group.created_at,
        updated_at=group.updated_at,
        role=member.role,
        member_count=count_group_members(db, group.id) if member_count is None else member_count,
        unread_count=unread_count or 0,
    )


def create_group(db: Session, user: User, payload: GroupCreate) -> GroupRead:
    try:
        group = Group(
            name=payload.name.strip(),
            description=payload.description.strip(),
            owner_id=user.id,
            is_public=payload.is_public,
        )
        db.add(group)
        db.flush()
        db.add(GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.OWNER))
        db.add(Conversation(group_id=group.id, name="General", created_by_id=user.id))
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - join_code collision
        db.rollback()
        raise ConflictError("Please try creating that group again.") from exc
    db.refresh(group)
    member = require_membership(db, group.id, user)
    return to_group_read(db, group, member, member_count=1, unread_count=0)


def list_my_groups(db: Session, user: User, params: PageParams) -> Page[GroupRead]:
    statement = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id)
        .order_by(Group.created_at.desc())
    )
    groups, total = _paginate_groups(db, statement, params)
    counts = member_counts(db, [group.id for group in groups])
    unread = unread_counts(db, user.id)
    members = {
        row.group_id: row
        for row in db.scalars(
            select(GroupMember).where(
                GroupMember.user_id == user.id, GroupMember.group_id.in_([g.id for g in groups])
            )
        )
    }
    return Page[GroupRead](
        items=[
            to_group_read(db, group, members[group.id], counts.get(group.id, 0), unread.get(group.id, 0))
            for group in groups
        ],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def discover_groups(db: Session, user: User, params: PageParams) -> Page[GroupSummary]:
    joined = select(GroupMember.group_id).where(GroupMember.user_id == user.id)
    statement = (
        select(Group)
        .where(Group.is_public.is_(True), Group.id.not_in(joined))
        .order_by(Group.created_at.desc())
    )
    groups, total = _paginate_groups(db, statement, params)
    counts = member_counts(db, [group.id for group in groups])
    return Page[GroupSummary](
        items=[
            GroupSummary(
                id=group.id,
                name=group.name,
                description=group.description,
                is_public=group.is_public,
                join_code=group.join_code,
                member_count=counts.get(group.id, 0),
                created_at=group.created_at,
            )
            for group in groups
        ],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def _paginate_groups(db: Session, statement, params: PageParams) -> tuple[list[Group], int]:
    rows, total = paginate(db, statement, params)
    return list(rows), total


def join_group(db: Session, user: User, code: str) -> GroupRead:
    group = db.scalar(select(Group).where(Group.join_code == code.strip().upper()))
    if group is None:
        raise ValidationError("That invite code isn't valid.")
    existing = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id, GroupMember.user_id == user.id
        )
    )
    if existing is not None:
        raise ConflictError("You are already a member of that group.")
    db.add(GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.MEMBER))
    db.commit()
    db.refresh(group)
    member = require_membership(db, group.id, user)
    return to_group_read(db, group, member)


def leave_group(db: Session, group_id: str, user: User) -> None:
    member = require_membership(db, group_id, user)
    group = get_group(db, group_id)
    remaining = count_group_members(db, group_id)

    if remaining == 1:
        # Last member out: the group has no audience left, so remove it and
        # its stored files rather than leaving an orphaned workspace.
        _delete_group_files(db, group_id)
        db.delete(group)
        db.commit()
        return

    if member.role is GroupRole.OWNER:
        _transfer_ownership(db, group_id)
    db.delete(member)
    db.commit()


def _transfer_ownership(db: Session, group_id: str) -> None:
    successor = db.scalars(
        select(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.role != GroupRole.OWNER)
        .order_by(
            # Prefer an existing admin, otherwise the longest-standing member.
            (GroupMember.role == GroupRole.ADMIN).desc(),
            GroupMember.joined_at.asc(),
        )
    ).first()
    if successor is None:
        raise ForbiddenError("This group has no other member who can take ownership yet.")
    successor.role = GroupRole.OWNER
    group = get_group(db, group_id)
    group.owner_id = successor.user_id
    db.flush()


def get_group_detail(db: Session, group_id: str, user: User) -> GroupRead:
    group = get_group(db, group_id)
    member = require_membership(db, group_id, user)
    unread = unread_counts(db, user.id).get(group_id, 0)
    return to_group_read(db, group, member, unread_count=unread)


def update_group(db: Session, group_id: str, user: User, payload: GroupUpdate) -> GroupRead:
    require_manager(db, group_id, user)
    group = get_group(db, group_id)
    if payload.name is not None:
        group.name = payload.name.strip()
    if payload.description is not None:
        group.description = payload.description.strip()
    if payload.is_public is not None:
        group.is_public = payload.is_public
    db.commit()
    db.refresh(group)
    member = require_membership(db, group_id, user)
    return to_group_read(db, group, member)


def delete_group(db: Session, group_id: str, user: User) -> None:
    require_owner(db, group_id, user)
    group = get_group(db, group_id)
    _delete_group_files(db, group_id)
    db.delete(group)
    db.commit()


def _delete_group_files(db: Session, group_id: str) -> None:
    """Remove stored bytes before the cascade removes their metadata rows."""
    storage = get_storage()
    for record in db.scalars(select(FileRecord).where(FileRecord.group_id == group_id)):
        storage.delete(record.storage_key)


def list_members(db: Session, group_id: str, user: User) -> list[GroupMemberRead]:
    require_membership(db, group_id, user)
    rows = db.scalars(
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at.asc())
    ).all()
    return [
        GroupMemberRead(
            user_id=member.user_id,
            username=member.user.username,
            full_name=member.user.full_name,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member in rows
    ]
