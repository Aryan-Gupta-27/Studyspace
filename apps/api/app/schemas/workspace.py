"""Note, file, project and task schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.workspace import ProjectStatus, TaskPriority, TaskStatus
from app.schemas.common import ORMModel
from app.schemas.users import UserBrief


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=100_000)
    group_id: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=100_000)


class NoteRead(ORMModel):
    id: str
    title: str
    body: str
    owner: UserBrief
    group_id: str | None
    created_at: datetime
    updated_at: datetime


class FileRead(ORMModel):
    id: str
    filename: str
    mime_type: str
    size: int
    owner: UserBrief
    group_id: str | None
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    status: ProjectStatus = ProjectStatus.PLANNING
    deadline: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None
    deadline: date | None = None


class ProjectRead(ORMModel):
    id: str
    group_id: str
    name: str
    description: str
    status: ProjectStatus
    deadline: date | None
    created_by: UserBrief
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    assignee_id: str | None = None
    deadline: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assignee_id: str | None = None
    deadline: date | None = None


class TaskMoveRequest(BaseModel):
    """Board drag-and-drop: change column and position in one call."""

    status: TaskStatus
    position: int = Field(ge=0, le=10_000)


class TaskRead(ORMModel):
    id: str
    project_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    position: int
    assignee: UserBrief | None
    created_by: UserBrief
    deadline: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
