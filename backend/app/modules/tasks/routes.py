"""Tasks & Projects module."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository


router = APIRouter(
    tags=["Tasks & Projects"],
    dependencies=[
        Depends(module_gate("tasks")),
        Depends(require_permission("tasks")),
    ],
)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_id: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"  # active | on_hold | completed | archived
    color: str = "#171717"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str = "todo"  # todo | in_progress | review | done
    priority: str = "medium"  # low | medium | high | urgent
    due_date: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    time_spent_minutes: int = 0


_projects: BaseRepository | None = None
_tasks: BaseRepository | None = None


def _project_repo() -> BaseRepository:
    global _projects

    if _projects is None:
        _projects = BaseRepository(
            get_db(),
            ProjectIn,
            "projects",
        )

    return _projects


def _task_repo() -> BaseRepository:
    global _tasks

    if _tasks is None:
        _tasks = BaseRepository(
            get_db(),
            TaskIn,
            "tasks",
        )

    return _tasks


# ─────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────


@router.get("/projects")
async def list_projects(user: UserDep):
    return await _project_repo().list(
        user.tenant_id,
        limit=500,
    )


@router.post("/projects", status_code=201)
async def create_project(
    body: ProjectIn,
    user: UserDep,
):
    return await _project_repo().create(
        user.tenant_id,
        body.model_dump(),
    )


@router.patch("/projects/{pid}")
async def update_project(
    pid: str,
    body: ProjectIn,
    user: UserDep,
):
    project = await _project_repo().update(
        user.tenant_id,
        pid,
        body.model_dump(),
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


@router.delete("/projects/{pid}", status_code=204)
async def delete_project(
    pid: str,
    user: UserDep,
):
    await _project_repo().delete(
        user.tenant_id,
        pid,
    )

    return None


# ─────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────


@router.get("/tasks")
async def list_tasks(
    user: UserDep,
    project_id: str | None = None,
    status_: str | None = None,
):
    filters: dict = {}

    if project_id:
        filters["project_id"] = project_id

    if status_:
        filters["status"] = status_

    return await _task_repo().list(
        user.tenant_id,
        filters,
        limit=1000,
    )


@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskIn,
    user: UserDep,
):
    return await _task_repo().create(
        user.tenant_id,
        body.model_dump(),
    )


@router.patch("/tasks/{tid}")
async def update_task(
    tid: str,
    body: TaskIn,
    user: UserDep,
):
    task = await _task_repo().update(
        user.tenant_id,
        tid,
        body.model_dump(),
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task


@router.delete("/tasks/{tid}", status_code=204)
async def delete_task(
    tid: str,
    user: UserDep,
):
    await _task_repo().delete(
        user.tenant_id,
        tid,
    )

    return None