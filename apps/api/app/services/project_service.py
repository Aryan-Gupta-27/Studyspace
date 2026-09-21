"""Projects and the task board.

Tasks move through TODO -> IN_PROGRESS -> REVIEW -> DONE. Every transition is
authorised against group membership and recorded with a completion timestamp
so the board is a real workflow rather than a label (RULEBOOK rule 96).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import paginate
from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import utcnow
from app.models.collaboration import GroupMember
from app.models.identity import User
from app.models.workspace import Project, Task, TaskStatus
from app.schemas.common import Page, PageParams
from app.schemas.users import UserBrief
from app.schemas.workspace import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    TaskCreate,
    TaskMoveRequest,
    TaskRead,
    TaskUpdate,
)
from app.services.permissions import (
    is_manager,
    require_manager,
    require_membership,
    require_project_access,
    require_task_access,
)

BOARD_COLUMNS = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW, TaskStatus.DONE]


def to_task_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        position=task.position,
        assignee=(
            UserBrief(
                id=task.assignee.id,
                username=task.assignee.username,
                full_name=task.assignee.full_name,
            )
            if task.assignee
            else None
        ),
        created_by=UserBrief(
            id=task.created_by.id,
            username=task.created_by.username,
            full_name=task.created_by.full_name,
        ),
        deadline=task.deadline,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _task_counts(db: Session, project_ids: list[str]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {project_id: {} for project_id in project_ids}
    if not project_ids:
        return counts
    rows = db.execute(
        select(Task.project_id, Task.status, func.count(Task.id))
        .where(Task.project_id.in_(project_ids))
        .group_by(Task.project_id, Task.status)
    ).all()
    for project_id, status, count in rows:
        counts.setdefault(project_id, {})[status.value] = int(count)
    return counts


def to_project_read(db: Session, project: Project, counts: dict[str, int] | None = None) -> ProjectRead:
    if counts is None:
        counts = _task_counts(db, [project.id]).get(project.id, {})
    return ProjectRead(
        id=project.id,
        group_id=project.group_id,
        name=project.name,
        description=project.description,
        status=project.status,
        deadline=project.deadline,
        created_by=UserBrief(
            id=project.created_by.id,
            username=project.created_by.username,
            full_name=project.created_by.full_name,
        ),
        created_at=project.created_at,
        updated_at=project.updated_at,
        task_counts=counts,
    )


def list_projects(db: Session, group_id: str, user: User, params: PageParams) -> Page[ProjectRead]:
    require_membership(db, group_id, user)
    statement = (
        select(Project).where(Project.group_id == group_id).order_by(Project.created_at.desc())
    )
    rows, total = paginate(db, statement, params)
    counts = _task_counts(db, [project.id for project in rows])
    return Page[ProjectRead](
        items=[to_project_read(db, project, counts.get(project.id, {})) for project in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def create_project(db: Session, group_id: str, user: User, payload: ProjectCreate) -> ProjectRead:
    require_membership(db, group_id, user)
    project = Project(
        group_id=group_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        status=payload.status,
        deadline=payload.deadline,
        created_by_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_project_read(db, project, {})


def get_project(db: Session, project_id: str, user: User) -> ProjectRead:
    project = require_project_access(db, project_id, user)
    return to_project_read(db, project)


def update_project(db: Session, project_id: str, user: User, payload: ProjectUpdate) -> ProjectRead:
    require_manager(db, require_project_access(db, project_id, user).group_id, user)
    project = require_project_access(db, project_id, user)
    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip()
    if payload.status is not None:
        project.status = payload.status
    if payload.deadline is not None:
        project.deadline = payload.deadline
    db.commit()
    db.refresh(project)
    return to_project_read(db, project)


def delete_project(db: Session, project_id: str, user: User) -> None:
    project = require_project_access(db, project_id, user)
    require_manager(db, project.group_id, user)
    db.delete(project)
    db.commit()


def list_tasks(db: Session, project_id: str, user: User, params: PageParams) -> Page[TaskRead]:
    require_project_access(db, project_id, user)
    statement = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.status.asc(), Task.position.asc(), Task.created_at.asc())
    )
    rows, total = paginate(db, statement, params)
    return Page[TaskRead](
        items=[to_task_read(task) for task in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def board(db: Session, project_id: str, user: User) -> dict[str, list[TaskRead]]:
    """Tasks grouped by column, in the order the board renders them."""
    require_project_access(db, project_id, user)
    tasks = db.scalars(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.position.asc(), Task.created_at.asc())
    ).all()
    grouped: dict[str, list[TaskRead]] = defaultdict(list)
    for task in tasks:
        grouped[task.status.value].append(to_task_read(task))
    return {column.value: grouped[column.value] for column in BOARD_COLUMNS}


def _next_position(db: Session, project_id: str, status: TaskStatus) -> int:
    current = db.scalar(
        select(func.coalesce(func.max(Task.position), -1)).where(
            Task.project_id == project_id, Task.status == status
        )
    )
    return int(current or -1) + 1


def _validate_assignee(db: Session, project: Project, assignee_id: str | None) -> None:
    if assignee_id is None:
        return
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == project.group_id, GroupMember.user_id == assignee_id
        )
    )
    if member is None:
        raise NotFoundError("That person isn't a member of this group.")


def create_task(db: Session, project_id: str, user: User, payload: TaskCreate) -> TaskRead:
    project = require_project_access(db, project_id, user)
    _validate_assignee(db, project, payload.assignee_id)
    task = Task(
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        priority=payload.priority,
        status=payload.status,
        position=_next_position(db, project_id, payload.status),
        assignee_id=payload.assignee_id,
        created_by_id=user.id,
        deadline=payload.deadline,
        completed_at=utcnow() if payload.status is TaskStatus.DONE else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return to_task_read(task)


def update_task(db: Session, task_id: str, user: User, payload: TaskUpdate) -> TaskRead:
    task = require_task_access(db, task_id, user)
    member = require_membership(db, task.project.group_id, user)
    if task.created_by_id != user.id and task.assignee_id != user.id and not is_manager(member):
        raise ForbiddenError("Only the task author, the assignee or a group admin can change this task.")

    project = task.project
    if payload.assignee_id is not None:
        _validate_assignee(db, project, payload.assignee_id)
    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description.strip()
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.deadline is not None:
        task.deadline = payload.deadline
    if payload.status is not None:
        _apply_status(task, payload.status, db, project.id)
    db.commit()
    db.refresh(task)
    return to_task_read(task)


def move_task(db: Session, task_id: str, user: User, payload: TaskMoveRequest) -> TaskRead:
    """Move a card to a column at a specific index (drag and drop on the board)."""
    task = require_task_access(db, task_id, user)
    require_membership(db, task.project.group_id, user)
    _apply_status(task, payload.status, db, task.project_id)
    task.position = payload.position
    db.commit()
    db.refresh(task)
    return to_task_read(task)


def _apply_status(task: Task, status: TaskStatus, db: Session, project_id: str) -> None:
    if task.status is status:
        return
    task.status = status
    task.position = _next_position(db, project_id, status)
    # Completion is derived from the column, so DONE is never out of sync.
    task.completed_at = utcnow() if status is TaskStatus.DONE else None


def delete_task(db: Session, task_id: str, user: User) -> None:
    task = require_task_access(db, task_id, user)
    member = require_membership(db, task.project.group_id, user)
    if task.created_by_id != user.id and not is_manager(member):
        raise ForbiddenError("Only the task author or a group admin can delete this task.")
    db.delete(task)
    db.commit()
