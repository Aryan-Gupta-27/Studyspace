"""Notes and files: the shared study material of a group.

Notes and files are either private (``group_id`` is NULL) or shared with a
group, and both cases are authorised server-side (RULEBOOK rules 22, 46).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import paginate
from app.core.errors import ForbiddenError, NotFoundError, PayloadTooLargeError, ValidationError
from app.models.collaboration import GroupMember
from app.models.identity import User
from app.models.workspace import FileRecord, Note
from app.schemas.common import Page, PageParams
from app.schemas.users import UserBrief
from app.schemas.workspace import FileRead, NoteCreate, NoteRead, NoteUpdate
from app.services.permissions import (
    is_manager,
    require_membership,
    require_note_access,
    require_note_delete_access,
    require_note_edit_access,
)
from app.services.storage import build_storage_key, get_storage

# Extensions that must never be accepted: anything a browser or server might
# execute. Everything else is stored and always served as an attachment.
BLOCKED_EXTENSIONS = {
    ".exe",
    ".sh",
    ".bash",
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".js",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".pl",
    ".jar",
    ".html",
    ".htm",
    ".svg",
    ".xhtml",
}


def _member_group_ids(db: Session, user: User) -> list[str]:
    return list(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user.id)).all())


def _owned_or_shared(
    db: Session, user: User, model: type[Note] | type[FileRecord]
) -> ColumnElement[bool]:
    """Rows the caller owns privately, plus everything shared with their groups.

    ``["__none__"]`` keeps the ``IN`` clause valid for users with no groups
    instead of building a different query shape for that case.
    """
    group_ids = _member_group_ids(db, user)
    return or_(model.owner_id == user.id, model.group_id.in_(group_ids or ["__none__"]))


def to_note_read(note: Note) -> NoteRead:
    return NoteRead(
        id=note.id,
        title=note.title,
        body=note.body,
        owner=UserBrief(
            id=note.owner.id, username=note.owner.username, full_name=note.owner.full_name
        ),
        group_id=note.group_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def list_notes(
    db: Session, user: User, params: PageParams, group_id: str | None = None, search: str | None = None
) -> Page[NoteRead]:
    statement = select(Note)
    if group_id is not None:
        require_membership(db, group_id, user)
        statement = statement.where(Note.group_id == group_id)
    else:
        statement = statement.where(_owned_or_shared(db, user, Note))
    if search:
        # Filtered in SQL so the page and the total both respect the query.
        needle = f"%{search.strip().lower()}%"
        statement = statement.where(
            or_(func.lower(Note.title).like(needle), func.lower(Note.body).like(needle))
        )
    statement = statement.order_by(Note.updated_at.desc())
    rows, total = paginate(db, statement, params)
    return Page[NoteRead](
        items=[to_note_read(note) for note in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def create_note(db: Session, user: User, payload: NoteCreate) -> NoteRead:
    if payload.group_id is not None:
        require_membership(db, payload.group_id, user)
    note = Note(
        title=payload.title.strip(),
        body=payload.body,
        owner_id=user.id,
        group_id=payload.group_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return to_note_read(note)


def get_note(db: Session, note_id: str, user: User) -> NoteRead:
    return to_note_read(require_note_access(db, note_id, user))


def update_note(db: Session, note_id: str, user: User, payload: NoteUpdate) -> NoteRead:
    note = require_note_edit_access(db, note_id, user)
    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.body is not None:
        note.body = payload.body
    db.commit()
    db.refresh(note)
    return to_note_read(note)


def delete_note(db: Session, note_id: str, user: User) -> None:
    note = require_note_delete_access(db, note_id, user)
    db.delete(note)
    db.commit()


def to_file_read(record: FileRecord) -> FileRead:
    return FileRead(
        id=record.id,
        filename=record.filename,
        mime_type=record.mime_type,
        size=record.size,
        owner=UserBrief(
            id=record.owner.id, username=record.owner.username, full_name=record.owner.full_name
        ),
        group_id=record.group_id,
        created_at=record.created_at,
    )


def list_files(db: Session, user: User, params: PageParams, group_id: str | None = None) -> Page[FileRead]:
    statement = select(FileRecord)
    if group_id is not None:
        require_membership(db, group_id, user)
        statement = statement.where(FileRecord.group_id == group_id)
    else:
        statement = statement.where(_owned_or_shared(db, user, FileRecord))
    statement = statement.order_by(FileRecord.created_at.desc())
    rows, total = paginate(db, statement, params)
    return Page[FileRead](
        items=[to_file_read(record) for record in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def _validate_upload(filename: str, mime_type: str, size: int, settings: Settings) -> str:
    # The client name is used for display only, and even then reduced to a bare
    # basename so it can never smuggle a path into the UI or storage key.
    safe_name = Path(filename.replace("\\", "/")).name.strip() or "file"
    if len(safe_name) > 200:
        safe_name = safe_name[-200:]
    extension = Path(safe_name).suffix.lower()
    if extension in BLOCKED_EXTENSIONS:
        raise ValidationError(f"Files of type {extension or 'unknown'} cannot be uploaded.")
    if size <= 0:
        raise ValidationError("That file is empty.")
    if size > settings.upload_max_bytes:
        limit_mb = settings.upload_max_bytes // (1024 * 1024)
        raise PayloadTooLargeError(f"Files must be {limit_mb} MB or smaller.")
    del mime_type  # recorded for display; never trusted for behaviour
    return safe_name


def upload_file(
    db: Session,
    user: User,
    group_id: str | None,
    filename: str,
    mime_type: str,
    data: bytes,
    settings: Settings,
) -> FileRecord:
    if group_id is not None:
        require_membership(db, group_id, user)
    safe_name = _validate_upload(filename, mime_type, len(data), settings)

    record = FileRecord(
        owner_id=user.id,
        group_id=group_id,
        filename=safe_name,
        mime_type=(mime_type or "application/octet-stream")[:255],
        size=len(data),
        storage_key="",  # replaced once the id exists
    )
    db.add(record)
    db.flush()
    record.storage_key = build_storage_key(group_id or f"user-{user.id}", record.id, safe_name)

    storage = get_storage(settings)
    try:
        storage.save(record.storage_key, data)
    except Exception as exc:
        # Never keep a metadata row pointing at bytes that were not stored.
        db.rollback()
        raise ValidationError("We couldn't save that file. Please try again.") from exc

    db.commit()
    db.refresh(record)
    return record


def get_file_for_download(db: Session, file_id: str, user: User) -> FileRecord:
    record = db.get(FileRecord, file_id)
    if record is None:
        raise NotFoundError("We couldn't find that file.")
    if record.group_id is None:
        if record.owner_id != user.id:
            raise ForbiddenError("That file is private.")
        return record
    require_membership(db, record.group_id, user)
    return record


def delete_file(db: Session, file_id: str, user: User) -> None:
    record = db.get(FileRecord, file_id)
    if record is None:
        raise NotFoundError("We couldn't find that file.")
    if record.group_id is None:
        if record.owner_id != user.id:
            raise ForbiddenError("That file is private.")
    else:
        member = require_membership(db, record.group_id, user)
        if record.owner_id != user.id and not is_manager(member):
            raise ForbiddenError("Only the person who uploaded this file or a group admin can delete it.")

    storage = get_storage()
    try:
        storage.delete(record.storage_key)
    finally:
        # Metadata is removed even if the blob is already gone, so a missing
        # object can never leave an undeletable row behind.
        db.delete(record)
        db.commit()
