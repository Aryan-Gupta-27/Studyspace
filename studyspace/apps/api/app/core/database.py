"""Single database access layer for the MVP.

The MVP runs on SQLite for a zero-dependency local setup, but every column
type and constraint is chosen so the same models migrate to PostgreSQL
unchanged (task book: "schema uses SQLAlchemy and remains
PostgreSQL-compatible").
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Engine, Select, String, TypeDecorator, create_engine, event, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings
from app.core.security import utcnow

if TYPE_CHECKING:  # pragma: no cover - import cycle only for typing
    from app.schemas.common import PageParams


def new_uuid() -> str:
    """Consistent identifier strategy: UUIDv4 rendered as a 36-char string.

    Stored as ``String(36)`` rather than a native UUID type so SQLite and
    PostgreSQL behave identically (RULEBOOK rule 121).
    """
    return str(uuid.uuid4())


class UTCDateTime(TypeDecorator):
    """Timestamp column that always stores and returns UTC.

    SQLite has no timezone-aware datetime type, so a naive value comes back
    from a round trip while PostgreSQL keeps the offset. Normalising in one
    place means the two engines are interchangeable and comparisons against
    ``utcnow()`` never fail (RULEBOOK rule 120).
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base shared by every domain model."""

    type_annotation_map = {datetime: UTCDateTime}


class TimestampMixin:
    """Created/updated timestamps, always stored in UTC."""

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


def _engine_kwargs(database_url: str) -> dict[str, Any]:
    if database_url.startswith("sqlite"):
        # SQLite needs this because the same connection is shared across the
        # request thread and the synchronous session in tests.
        return {"connect_args": {"check_same_thread": False}}
    return {}


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    engine = create_engine(url, future=True, **_engine_kwargs(url))
    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless enabled per connection.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_connection: Any, _record: Any) -> None:  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    """Create tables for local development and tests.

    Production schema changes go through Alembic migrations instead
    (RULEBOOK rule 24).
    """
    import app.models  # noqa: F401  (import registers every model on Base)

    Base.metadata.create_all(engine)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_database(database_url: str | None = None) -> Engine:
    """(Re)bind the process-wide engine. Tests call this with a throwaway URL."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = create_database_engine(database_url)
    _session_factory = create_session_factory(_engine)
    return _engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        configure_database()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        configure_database()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding one transaction-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def paginate(db: Session, statement: Select[tuple[Any, ...]], params: PageParams) -> tuple[list[Any], int]:
    """Apply a bounded limit/offset window and return ``(rows, total_count)``."""
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(db.scalars(statement.limit(params.limit).offset(params.offset)))
    return rows, int(total)
