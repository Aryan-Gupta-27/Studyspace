"""Group chat: conversations, paginated messages and unread state.

Realtime delivery is deliberately HTTP polling for the MVP; WebSockets are
deferred until after the MVP gate (task book, milestone 4).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import paginate
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.security import utcnow
from app.models.collaboration import Conversation, GroupMember, Message
from app.models.identity import User
from app.schemas.common import Page, PageParams
from app.schemas.groups import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
    MessageUpdate,
)
from app.schemas.users import UserBrief
from app.services.group_service import unread_counts
from app.services.permissions import (
    is_manager,
    require_conversation_access,
    require_membership,
)


def to_message_read(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        author=UserBrief(
            id=message.author.id,
            username=message.author.username,
            full_name=message.author.full_name,
        ),
        body=message.body,
        created_at=message.created_at,
        edited_at=message.edited_at,
    )


def list_conversations(db: Session, group_id: str, user: User) -> list[ConversationRead]:
    require_membership(db, group_id, user)
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.group_id == group_id)
        .order_by(Conversation.created_at.asc())
    ).all()
    if not conversations:
        return []

    last_message_at: dict[str, datetime] = {}
    for conversation_id, last_at in db.execute(
        select(Message.conversation_id, func.max(Message.created_at))
        .where(Message.conversation_id.in_([c.id for c in conversations]))
        .group_by(Message.conversation_id)
    ).all():
        last_message_at[str(conversation_id)] = last_at
    return [
        ConversationRead(
            id=conversation.id,
            group_id=conversation.group_id,
            name=conversation.name,
            created_at=conversation.created_at,
            last_message_at=last_message_at.get(conversation.id),
        )
        for conversation in conversations
    ]


def create_conversation(
    db: Session, group_id: str, user: User, payload: ConversationCreate
) -> ConversationRead:
    require_membership(db, group_id, user)
    conversation = Conversation(group_id=group_id, name=payload.name.strip(), created_by_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ConversationRead(
        id=conversation.id,
        group_id=conversation.group_id,
        name=conversation.name,
        created_at=conversation.created_at,
        last_message_at=None,
    )


def list_messages(db: Session, conversation_id: str, user: User, params: PageParams) -> Page[MessageRead]:
    conversation = require_conversation_access(db, conversation_id, user)
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
    )
    rows, total = paginate(db, statement, params)
    # The query walks backwards from the newest message; the UI renders oldest
    # first, so the page is reversed before it leaves the service.
    return Page[MessageRead](
        items=[to_message_read(message) for message in reversed(rows)],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def create_message(db: Session, conversation_id: str, user: User, payload: MessageCreate) -> MessageRead:
    conversation = require_conversation_access(db, conversation_id, user)
    body = payload.body.strip()
    if not body:
        raise ValidationError("Write something before sending.")
    message = Message(conversation_id=conversation.id, author_id=user.id, body=body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return to_message_read(message)


def update_message(db: Session, message_id: str, user: User, payload: MessageUpdate) -> MessageRead:
    message = db.get(Message, message_id)
    if message is None:
        raise NotFoundError("We couldn't find that message.")
    require_conversation_access(db, message.conversation_id, user)
    if message.author_id != user.id:
        raise ForbiddenError("You can only edit your own messages.")
    body = payload.body.strip()
    if not body:
        raise ValidationError("Write something before saving.")
    message.body = body
    message.edited_at = utcnow()
    db.commit()
    db.refresh(message)
    return to_message_read(message)


def delete_message(db: Session, message_id: str, user: User) -> None:
    message = db.get(Message, message_id)
    if message is None:
        raise NotFoundError("We couldn't find that message.")
    member = require_membership(db, message.conversation.group_id, user)
    if message.author_id != user.id and not is_manager(member):
        raise ForbiddenError("You can only delete your own messages.")
    db.delete(message)
    db.commit()


def mark_conversation_read(db: Session, conversation_id: str, user: User) -> None:
    """Advance the caller's unread watermark for the owning group."""
    conversation = require_conversation_access(db, conversation_id, user)
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == conversation.group_id, GroupMember.user_id == user.id
        )
    )
    if member is not None:
        member.last_read_at = utcnow()
        db.commit()


def unread_count(db: Session, group_id: str, user: User) -> int:
    require_membership(db, group_id, user)
    return unread_counts(db, user.id).get(group_id, 0)
