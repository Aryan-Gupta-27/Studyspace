"""Group, membership, conversation and message schemas.

Chat lives in this module because a conversation only ever exists inside a
group, so the two are requested and rendered together.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.collaboration import GroupRole
from app.schemas.common import ORMModel
from app.schemas.users import UserBrief


class GroupCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    is_public: bool = True


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


class GroupJoinRequest(BaseModel):
    code: str = Field(min_length=4, max_length=10)


class GroupMemberRead(ORMModel):
    user_id: str
    username: str
    full_name: str
    role: GroupRole
    joined_at: datetime


class GroupRead(ORMModel):
    id: str
    name: str
    description: str
    owner_id: str
    is_public: bool
    join_code: str
    created_at: datetime
    updated_at: datetime
    role: GroupRole
    member_count: int
    unread_count: int


class ConversationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ConversationRead(ORMModel):
    id: str
    group_id: str
    name: str
    created_at: datetime
    last_message_at: datetime | None = None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @property
    def cleaned(self) -> str:
        return self.body.strip()


class MessageUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageRead(ORMModel):
    id: str
    conversation_id: str
    author: UserBrief
    body: str
    created_at: datetime
    edited_at: datetime | None = None


class GroupSummary(ORMModel):
    """Public group as shown on the discover screen, before you are a member."""

    id: str
    name: str
    description: str
    is_public: bool
    join_code: str
    member_count: int
    created_at: datetime
