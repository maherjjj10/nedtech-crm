"""Tasks & Projects module."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import (
    BaseRepository,
    new_id,
    utcnow_iso,
)


router = APIRouter(
    tags=["Tasks & Projects"],
    dependencies=[
        Depends(module_gate("tasks")),
        Depends(require_permission("tasks")),
    ],
)


class ProjectIn(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    client_id: Optional[str] = None
    description: Optional[str] = None

    status: str = "active"

    color: str = "#171717"

    start_date: Optional[str] = None
    end_date: Optional[str] = None


class TaskIn(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: Optional[str] = None

    project_id: Optional[str] = None

    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None

    status: str = "todo"

    priority: str = "medium"

    due_date: Optional[str] = None

    tags: list[str] = Field(
        default_factory=list
    )

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


# ============================================================
# NOTIFICATIONS
# ============================================================

async def _create_task_notification(
    *,
    tenant_id: str,
    user_id: str,
    title: str,
    message: str,
    task_id: str,
    notification_type: str,
):
    notification_id = new_id()

    await get_db().notifications.insert_one(
        {
            "_id": notification_id,
            "id": notification_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "entity_type": "task",
            "entity_id": task_id,
            "url": "/tasks",
            "read": False,
            "created_at": utcnow_iso(),
        }
    )


async def _find_employee(
    tenant_id: str,
    employee_id: str,
):
    return await get_db().employees.find_one(
        {
            "tenant_id": tenant_id,
            "id": employee_id,
            "status": "active",
        },
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "email": 1,
        },
    )


# ============================================================
# PROJECTS
# ============================================================

@router.get("/projects")
async def list_projects(
    user: UserDep,
):
    return await _project_repo().list(
        user.tenant_id,
        limit=500,
    )


@router.post(
    "/projects",
    status_code=201,
)
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


@router.delete(
    "/projects/{pid}",
    status_code=204,
)
async def delete_project(
    pid: str,
    user: UserDep,
):
    project = await _project_repo().get(
        user.tenant_id,
        pid,
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    await _project_repo().delete(
        user.tenant_id,
        pid,
    )

    return None


# ============================================================
# TASKS
# ============================================================

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


@router.post(
    "/tasks",
    status_code=201,
)
async def create_task(
    body: TaskIn,
    user: UserDep,
):
    task = await _task_repo().create(
        user.tenant_id,
        body.model_dump(),
    )

    # --------------------------------------------------------
    # Notify assigned employee
    # --------------------------------------------------------

    if body.assignee_id:
        employee = await _find_employee(
            user.tenant_id,
            body.assignee_id,
        )

        if employee and employee.get("email"):
            await _create_task_notification(
                tenant_id=user.tenant_id,
                user_id=employee["email"],
                title="New task assigned",
                message=(
                    f"You have been assigned "
                    f"the task: {body.title}"
                ),
                task_id=task["id"],
                notification_type="task_assigned",
            )

    # --------------------------------------------------------
    # No assignee → notify creator
    # --------------------------------------------------------

    else:
        await _create_task_notification(
            tenant_id=user.tenant_id,
            user_id=user.email,
            title="New task created",
            message=body.title,
            task_id=task["id"],
            notification_type="task_created",
        )

    return task


@router.patch("/tasks/{tid}")
async def update_task(
    tid: str,
    body: TaskIn,
    user: UserDep,
):
    old_task = await _task_repo().get(
        user.tenant_id,
        tid,
    )

    if not old_task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    updated = await _task_repo().update(
        user.tenant_id,
        tid,
        body.model_dump(),
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    old_assignee_id = old_task.get(
        "assignee_id"
    )

    new_assignee_id = body.assignee_id

    # --------------------------------------------------------
    # Assignment changed
    # --------------------------------------------------------

    if (
        new_assignee_id
        and new_assignee_id != old_assignee_id
    ):
        employee = await _find_employee(
            user.tenant_id,
            new_assignee_id,
        )

        if employee and employee.get("email"):
            await _create_task_notification(
                tenant_id=user.tenant_id,
                user_id=employee["email"],
                title="Task assigned to you",
                message=(
                    f"You have been assigned "
                    f"the task: {body.title}"
                ),
                task_id=updated["id"],
                notification_type="task_assigned",
            )

    # --------------------------------------------------------
    # Status changed
    # --------------------------------------------------------

    old_status = old_task.get(
        "status"
    )

    new_status = body.status

    if (
        old_status
        and new_status
        and old_status != new_status
    ):
        notification_email = None

        if new_assignee_id:
            employee = await _find_employee(
                user.tenant_id,
                new_assignee_id,
            )

            if employee:
                notification_email = employee.get(
                    "email"
                )

        if notification_email:
            await _create_task_notification(
                tenant_id=user.tenant_id,
                user_id=notification_email,
                title="Task status updated",
                message=(
                    f"Task '{body.title}' "
                    f"changed from "
                    f"{old_status} to "
                    f"{new_status}"
                ),
                task_id=updated["id"],
                notification_type="task_status",
            )

    return updated


@router.delete(
    "/tasks/{tid}",
    status_code=204,
)
async def delete_task(
    tid: str,
    user: UserDep,
):
    task = await _task_repo().get(
        user.tenant_id,
        tid,
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    await _task_repo().delete(
        user.tenant_id,
        tid,
    )

    return None