"""Group endpoints: create, discover, join, leave, update, delete, members."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.schemas.groups import (
    GroupCreate,
    GroupJoinRequest,
    GroupMemberRead,
    GroupRead,
    GroupSummary,
    GroupUpdate,
)
from app.schemas.workspace import FileRead, NoteRead
from app.services import content_service, group_service

router = APIRouter(tags=["groups"])


@router.post("/groups", response_model=GroupRead, status_code=201)
def create_group(payload: GroupCreate, db: DatabaseSession, current_user: CurrentUser) -> GroupRead:
    return group_service.create_group(db, current_user, payload)


@router.get("/groups", response_model=Page[GroupRead])
def list_my_groups(
    db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[GroupRead]:
    return group_service.list_my_groups(db, current_user, pagination)


@router.get("/groups/discover", response_model=Page[GroupSummary])
def discover_groups(
    db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[GroupSummary]:
    return group_service.discover_groups(db, current_user, pagination)


@router.post("/groups/join", response_model=GroupRead)
def join_group(payload: GroupJoinRequest, db: DatabaseSession, current_user: CurrentUser) -> GroupRead:
    return group_service.join_group(db, current_user, payload.code)


@router.get("/groups/{group_id}", response_model=GroupRead)
def read_group(group_id: str, db: DatabaseSession, current_user: CurrentUser) -> GroupRead:
    return group_service.get_group_detail(db, group_id, current_user)


@router.patch("/groups/{group_id}", response_model=GroupRead)
def update_group(
    group_id: str, payload: GroupUpdate, db: DatabaseSession, current_user: CurrentUser
) -> GroupRead:
    return group_service.update_group(db, group_id, current_user, payload)


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    group_service.delete_group(db, group_id, current_user)


@router.post("/groups/{group_id}/leave", status_code=204)
def leave_group(group_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    group_service.leave_group(db, group_id, current_user)


@router.get("/groups/{group_id}/members", response_model=list[GroupMemberRead])
def list_members(group_id: str, db: DatabaseSession, current_user: CurrentUser) -> list[GroupMemberRead]:
    return group_service.list_members(db, group_id, current_user)


@router.get("/groups/{group_id}/notes", response_model=Page[NoteRead])
def list_group_notes(
    group_id: str,
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Pagination,
    search: str | None = Query(default=None, max_length=100),
) -> Page[NoteRead]:
    return content_service.list_notes(db, current_user, pagination, group_id=group_id, search=search)


@router.get("/groups/{group_id}/files", response_model=Page[FileRead])
def list_group_files(
    group_id: str, db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[FileRead]:
    return content_service.list_files(db, current_user, pagination, group_id=group_id)
