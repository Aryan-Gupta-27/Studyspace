"""File endpoints: upload, list, download (always as an attachment), delete."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.dependencies import CurrentUser, DatabaseSession, Pagination, SettingsDep
from app.core.errors import ValidationError
from app.core.rate_limit import limit_upload
from app.schemas.common import Page
from app.schemas.workspace import FileRead
from app.services import content_service
from app.services.storage import get_storage

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileRead, status_code=201)
async def upload_file(
    request: Request,
    db: DatabaseSession,
    settings: SettingsDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    group_id: str | None = Form(default=None),
) -> FileRead:
    limit_upload(request, settings, current_user.id)
    if file.filename is None:
        raise ValidationError("Choose a file to upload.")
    # Size is checked from the stream as it is read so an oversized body never
    # lands in memory.
    data = await _read_capped(file, settings.upload_max_bytes)
    record = content_service.upload_file(
        db,
        current_user,
        group_id,
        file.filename,
        file.content_type or "application/octet-stream",
        data,
        settings,
    )
    return content_service.to_file_read(record)


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise ValidationError("That file is larger than the allowed limit.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("", response_model=Page[FileRead])
def list_files(
    db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[FileRead]:
    return content_service.list_files(db, current_user, pagination)


@router.get("/{file_id}")
def download_file(file_id: str, db: DatabaseSession, current_user: CurrentUser) -> FileResponse:
    record = content_service.get_file_for_download(db, file_id, current_user)
    path = get_storage().resolve(record.storage_key)
    # Served as an opaque attachment: the browser must never render uploaded
    # content inline, otherwise a .html upload becomes stored XSS.
    return FileResponse(
        path=path,
        filename=record.filename.replace('"', "").replace("\n", ""),
        media_type="application/octet-stream",
    )


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    content_service.delete_file(db, file_id, current_user)
