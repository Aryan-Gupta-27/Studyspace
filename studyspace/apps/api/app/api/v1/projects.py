"""Project and task board endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.schemas.workspace import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    TaskCreate,
    TaskMoveRequest,
    TaskRead,
    TaskUpdate,
)
from app.services import project_service

router = APIRouter(tags=["projects"])


@router.get("/groups/{group_id}/projects", response_model=Page[ProjectRead])
def list_projects(
    group_id: str, db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[ProjectRead]:
    return project_service.list_projects(db, group_id, current_user, pagination)


@router.post("/groups/{group_id}/projects", response_model=ProjectRead, status_code=201)
def create_project(
    group_id: str, payload: ProjectCreate, db: DatabaseSession, current_user: CurrentUser
) -> ProjectRead:
    return project_service.create_project(db, group_id, current_user, payload)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def read_project(project_id: str, db: DatabaseSession, current_user: CurrentUser) -> ProjectRead:
    return project_service.get_project(db, project_id, current_user)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str, payload: ProjectUpdate, db: DatabaseSession, current_user: CurrentUser
) -> ProjectRead:
    return project_service.update_project(db, project_id, current_user, payload)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    project_service.delete_project(db, project_id, current_user)


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskRead])
def list_tasks(
    project_id: str, db: DatabaseSession, current_user: CurrentUser, pagination: Pagination
) -> Page[TaskRead]:
    return project_service.list_tasks(db, project_id, current_user, pagination)


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
def create_task(
    project_id: str, payload: TaskCreate, db: DatabaseSession, current_user: CurrentUser
) -> TaskRead:
    return project_service.create_task(db, project_id, current_user, payload)


@router.get("/projects/{project_id}/board", response_model=dict[str, list[TaskRead]])
def read_board(project_id: str, db: DatabaseSession, current_user: CurrentUser) -> dict[str, list[TaskRead]]:
    return project_service.board(db, project_id, current_user)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str, payload: TaskUpdate, db: DatabaseSession, current_user: CurrentUser
) -> TaskRead:
    return project_service.update_task(db, task_id, current_user, payload)


@router.post("/tasks/{task_id}/move", response_model=TaskRead)
def move_task(
    task_id: str, payload: TaskMoveRequest, db: DatabaseSession, current_user: CurrentUser
) -> TaskRead:
    return project_service.move_task(db, task_id, current_user, payload)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, db: DatabaseSession, current_user: CurrentUser) -> None:
    project_service.delete_task(db, task_id, current_user)
