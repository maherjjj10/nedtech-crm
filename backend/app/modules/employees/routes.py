"""Employees / team members within the tenant."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.deps import (
    UserDep,
    require_permission,
    require_tenant_role,
)
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository, utcnow_iso, new_id
from app.core.roles import (
    normalize_permissions,
    normalize_tenant_role,
    TENANT_ROLES,
    effective_rank,
)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
    dependencies=[Depends(module_gate("hr"))],
)


class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    # admin | manager | employee | viewer
    role: str = "employee"

    department: Optional[str] = None
    position: Optional[str] = None

    salary: float = 0
    currency: str = "USD"

    hire_date: Optional[str] = None

    # active | on_leave | terminated
    status: str = "active"

    avatar_url: Optional[str] = None

    permissions: Optional[dict[str, bool]] = None


class EmployeePermissionsUpdate(BaseModel):
    permissions: dict[str, bool]


class EmployeeRoleUpdate(BaseModel):
    role: str


_repo: BaseRepository | None = None


def _get_repo() -> BaseRepository:
    global _repo

    if _repo is None:
        _repo = BaseRepository(
            get_db(),
            EmployeeIn,
            "employees",
        )

    return _repo


async def _get_employee(
    tenant_id: str,
    employee_id: str,
):
    return await get_db().employees.find_one(
        {
            "tenant_id": tenant_id,
            "id": employee_id,
        },
        {"_id": 0},
    )


def _can_manage_employee(actor: UserDep, target: dict) -> bool:
    """
    Determine whether the current user can manage another employee.

    Rules:
    - platform admins bypass tenant restrictions
    - tenant admin can manage everyone
    - manager can manage employees/viewers
    - employee/viewer cannot manage others
    - nobody can manage an account with a higher role
    """

    if actor.is_platform_admin:
        return True

    actor_rank = effective_rank(
        actor.platform_role,
        actor.role,
    )

    target_role = normalize_tenant_role(
        target.get("role")
    ) or "viewer"

    target_rank = effective_rank(
        None,
        target_role,
    )

    if actor.role == "admin":
        return True

    if actor.role == "manager":
        return (
            target_role in {"employee", "viewer"}
            and actor_rank >= target_rank
        )

    return False


# ------------------------------------------------------------
# Employees
# ------------------------------------------------------------

@router.get("")
async def list_employees(user: UserDep):
    employees = await _get_repo().list(
        user.tenant_id,
        limit=500,
    )

    for employee in employees:
        employee["permissions"] = normalize_permissions(
            employee.get("permissions")
        )

    return employees


@router.post("", status_code=201)
async def create_employee(
    body: EmployeeIn,
    user: UserDep,
):
    role = normalize_tenant_role(body.role)

    if role not in TENANT_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid employee role",
        )

    # Only admins/platform admins can create managers/admins.
    if role in {"admin", "manager"} and not user.is_platform_admin:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can create admin or manager employees",
            )

    data = body.model_dump()

    data["role"] = role
    data["permissions"] = normalize_permissions(
        data.get("permissions")
    )

    return await _get_repo().create(
        user.tenant_id,
        data,
    )


@router.patch("/{eid}")
async def update_employee(
    eid: str,
    body: EmployeeIn,
    user: UserDep,
):
    employee = await _get_employee(
        user.tenant_id,
        eid,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if not _can_manage_employee(user, employee):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to manage this employee",
        )

    role = normalize_tenant_role(body.role)

    if role not in TENANT_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid employee role",
        )

    # A manager cannot promote someone to manager/admin.
    if user.role == "manager" and role not in {
        "employee",
        "viewer",
    }:
        raise HTTPException(
            status_code=403,
            detail="Managers cannot assign admin or manager roles",
        )

    data = body.model_dump()

    data["role"] = role
    data["permissions"] = normalize_permissions(
        data.get("permissions")
    )

    updated = await _get_repo().update(
        user.tenant_id,
        eid,
        data,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    updated["permissions"] = normalize_permissions(
        updated.get("permissions")
    )

    return updated


# ------------------------------------------------------------
# Permissions
# ------------------------------------------------------------

@router.get("/{eid}/permissions")
async def get_employee_permissions(
    eid: str,
    user: UserDep,
):
    employee = await _get_employee(
        user.tenant_id,
        eid,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if not _can_manage_employee(user, employee):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this employee's permissions",
        )

    return {
        "employee_id": employee["id"],
        "name": employee.get("name"),
        "role": employee.get("role"),
        "permissions": normalize_permissions(
            employee.get("permissions")
        ),
    }


@router.patch("/{eid}/permissions")
async def update_employee_permissions(
    eid: str,
    body: EmployeePermissionsUpdate,
    user: UserDep,
):
    employee = await _get_employee(
        user.tenant_id,
        eid,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if employee["id"] == user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot change your own permissions",
        )

    if not _can_manage_employee(user, employee):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to change this employee's permissions",
        )

    permissions = normalize_permissions(
        body.permissions
    )

    before = normalize_permissions(
        employee.get("permissions")
    )

    await get_db().users.update_one(
        {
            "id": employee["id"],
            "tenant_id": user.tenant_id,
        },
        {
            "$set": {
                "permissions": permissions,
                "updated_at": utcnow_iso(),
            }
        },
    )

    await get_db().employees.update_one(
        {
            "id": employee["id"],
            "tenant_id": user.tenant_id,
        },
        {
            "$set": {
                "permissions": permissions,
                "updated_at": utcnow_iso(),
            }
        },
    )

    await get_db().activities.insert_one(
        {
            "_id": new_id(),
            "id": new_id(),
            "tenant_id": user.tenant_id,
            "type": "employee_permissions_updated",
            "entity_id": employee["id"],
            "message": (
                f"Permissions updated for "
                f"employee '{employee.get('name', employee['id'])}'"
            ),
            "actor": user.email,
            "created_at": utcnow_iso(),
            "before": before,
            "after": permissions,
        }
    )

    return {
        "employee_id": employee["id"],
        "permissions": permissions,
    }


# ------------------------------------------------------------
# Role
# ------------------------------------------------------------

@router.patch("/{eid}/role")
async def update_employee_role(
    eid: str,
    body: EmployeeRoleUpdate,
    user: UserDep,
):
    employee = await _get_employee(
        user.tenant_id,
        eid,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if employee["id"] == user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot change your own role",
        )

    if not _can_manage_employee(user, employee):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to change this employee's role",
        )

    role = normalize_tenant_role(body.role)

    if role not in TENANT_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid employee role",
        )

    if user.role == "manager" and role not in {
        "employee",
        "viewer",
    }:
        raise HTTPException(
            status_code=403,
            detail="Managers cannot assign admin or manager roles",
        )

    old_role = employee.get("role")

    await get_db().users.update_one(
        {
            "id": employee["id"],
            "tenant_id": user.tenant_id,
        },
        {
            "$set": {
                "role": role,
                "updated_at": utcnow_iso(),
            }
        },
    )

    await get_db().employees.update_one(
        {
            "id": employee["id"],
            "tenant_id": user.tenant_id,
        },
        {
            "$set": {
                "role": role,
                "updated_at": utcnow_iso(),
            }
        },
    )

    await get_db().activities.insert_one(
        {
            "_id": new_id(),
            "id": new_id(),
            "tenant_id": user.tenant_id,
            "type": "employee_role_updated",
            "entity_id": employee["id"],
            "message": (
                f"Role changed for "
                f"employee '{employee.get('name', employee['id'])}'"
            ),
            "actor": user.email,
            "created_at": utcnow_iso(),
            "before": old_role,
            "after": role,
        }
    )

    return {
        "employee_id": employee["id"],
        "role": role,
    }


# ------------------------------------------------------------
# Delete
# ------------------------------------------------------------

@router.delete("/{eid}", status_code=204)
async def delete_employee(
    eid: str,
    user: UserDep,
):
    employee = await _get_employee(
        user.tenant_id,
        eid,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if employee["id"] == user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete yourself",
        )

    if not _can_manage_employee(user, employee):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this employee",
        )

    await _get_repo().delete(
        user.tenant_id,
        eid,
    )

    return None