"""Chat endpoints: conversations, paginated messages and the read watermark."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.schemas.groups import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
    MessageUpdate,
)
from app.services import chat_service

router = APIRouter(tags=["chat"])


@router.get("/groups/{group_id}/conversations", response_model=list[ConversationRead])
def list_conversations(group_id: str, db: DatabaseSession, current_user: CurrentUser) -> list[ConversationRead]:
    return chat_service.list_conversations(db, group_id, current_user)


@router.post("/groups/{group_id}/conversations", response_model=ConversationRead, status_code=201)
def create_conversation(
    group_id: str, payload: ConversationCreate, db: DatabaseSession, current_user: CurrentUser
) -> ConversationRead:
    return chat_service.create_conversation(db, group_id, current_user, payload)


@router.get("/conversations/{conversation_id}/messages", response_model=Page[MessageRead])
def list_messages(
    conversation_id: str, db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[MessageRead]:
    return chat_service.list_messages(db, conversation_id, current_user, pagination)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead, status_code=201)
def create_message(
    conversation_id: str, payload: MessageCreate, db: DatabaseSession, current_user: CurrentUser
) -> MessageRead:
    return chat_service.create_message(db, conversation_id, current_user, payload)


@router.post("/conversations/{conversation_id}/read", status_code=204)
def mark_read(conversation_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    chat_service.mark_conversation_read(db, conversation_id, current_user)


@router.patch("/messages/{message_id}", response_model=MessageRead)
def update_message(
    message_id: str, payload: MessageUpdate, db: DatabaseSession, current_user: CurrentUser
) -> MessageRead:
    return chat_service.update_message(db, message_id, current_user, payload)


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    chat_service.delete_message(db, message_id, current_user)
