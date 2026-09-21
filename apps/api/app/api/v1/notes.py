"""Note endpoints: personal and group notes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.schemas.workspace import NoteCreate, NoteRead, NoteUpdate
from app.services import content_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=Page[NoteRead])
def list_notes(
    db: DatabaseSession,
    current_user: CurrentUser,
    pagination: Pagination,
    search: str | None = Query(default=None, max_length=100),
) -> Page[NoteRead]:
    return content_service.list_notes(db, current_user, pagination, search=search)


@router.post("", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, db: DatabaseSession, current_user: CurrentUser) -> NoteRead:
    return content_service.create_note(db, current_user, payload)


@router.get("/{note_id}", response_model=NoteRead)
def read_note(note_id: str, db: DatabaseSession, current_user: CurrentUser) -> NoteRead:
    return content_service.get_note(db, note_id, current_user)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: str, payload: NoteUpdate, db: DatabaseSession, current_user: CurrentUser
) -> NoteRead:
    return content_service.update_note(db, note_id, current_user, payload)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    content_service.delete_note(db, note_id, current_user)
