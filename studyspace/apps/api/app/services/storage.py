"""File storage behind a service interface.

The MVP writes to the local filesystem. S3-compatible object storage is
deferred, so callers depend on the :class:`StorageBackend` protocol only and
the adapter can be swapped without touching any domain code (task book:
"local development storage behind a storage service interface").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError

# Storage keys are generated server-side. This is a defence-in-depth check: a
# key containing a separator or traversal sequence can never reach the disk.
_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_.-]{0,254}$")


class StorageBackend(Protocol):
    """Minimal contract every storage adapter must satisfy."""

    def save(self, key: str, data: bytes) -> None:
        """Persist ``data`` at ``key``, raising on any failure."""

    def resolve(self, key: str) -> Path:
        """Return a filesystem path for reading, or raise ``NotFoundError``."""

    def delete(self, key: str) -> None:
        """Remove the object at ``key``. Missing objects are ignored."""


class LocalStorageBackend:
    """Filesystem adapter rooted at ``base_dir``."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def _path_for(self, key: str) -> Path:
        if not _SAFE_KEY.match(key) or ".." in key:
            raise NotFoundError("That file is not available.")
        candidate = (self.base_dir / key).resolve()
        # resolve() also normalises symlinks, so this blocks escapes via links.
        if not str(candidate).startswith(str(self.base_dir.resolve())):
            raise NotFoundError("That file is not available.")
        return candidate

    def save(self, key: str, data: bytes) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_bytes(data)
        temp.replace(path)

    def resolve(self, key: str) -> Path:
        path = self._path_for(key)
        if not path.is_file():
            raise NotFoundError("That file is no longer available.")
        return path

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        path.unlink(missing_ok=True)


_backend: StorageBackend | None = None


def get_storage(settings: Settings | None = None) -> StorageBackend:
    """Cached accessor for the configured storage backend."""
    global _backend
    if _backend is None:
        resolved = settings or get_settings()
        resolved.storage_dir.mkdir(parents=True, exist_ok=True)
        _backend = LocalStorageBackend(resolved.storage_dir)
    return _backend


def configure_storage(backend: StorageBackend) -> None:
    """Override the backend. Used by tests to isolate uploads."""
    global _backend
    _backend = backend


def build_storage_key(scope: str, file_id: str, filename: str) -> str:
    """Create an opaque, traversal-safe key.

    The client-supplied filename contributes only a sanitised extension, so a
    name like ``../../etc/passwd`` can never influence the path (RULEBOOK
    rules 20, 21).
    """
    extension = sanitise_extension(filename)
    safe_scope = re.sub(r"[^A-Za-z0-9_-]", "_", scope) or "personal"
    return f"{safe_scope}/{file_id}{extension}"


def sanitise_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not suffix or len(suffix) > 10:
        return ""
    return "".join(char for char in suffix if char.isalnum() or char == ".")
