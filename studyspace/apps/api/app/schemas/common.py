"""Shared schema primitives: ORM-friendly base model and pagination."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for schemas that may be populated directly from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Envelope for every paginated collection (RULEBOOK rule 92)."""

    items: list[T]
    total: int
    limit: int
    offset: int


class PageParams:
    """Bounded pagination window shared by list endpoints."""

    __slots__ = ("limit", "offset")

    def __init__(self, limit: int, offset: int) -> None:
        self.limit = limit
        self.offset = offset
