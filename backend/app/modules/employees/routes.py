"""Employees / team members within the tenant."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository

router = APIRouter(prefix="/employees", tags=["Employees"], dependencies=[Depends(module_gate("hr"))])


class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str = "member"  # owner | admin | manager | member
    department: Optional[str] = None
    position: Optional[str] = None
    salary: float = 0
    currency: str = "USD"
    hire_date: Optional[str] = None
    status: str = "active"  # active | on_leave | terminated
    avatar_url: Optional[str] = None


_repo: BaseRepository | None = None


def _get_repo():
    global _repo
    if _repo is None:
        _repo = BaseRepository(get_db(), EmployeeIn, "employees")
    return _repo


@router.get("")
async def list_employees(user: UserDep):
    return await _get_repo().list(user.tenant_id, limit=500)


@router.post("", status_code=201)
async def create_employee(body: EmployeeIn, user: UserDep):
    return await _get_repo().create(user.tenant_id, body.model_dump())


@router.patch("/{eid}")
async def update_employee(eid: str, body: EmployeeIn, user: UserDep):
    d = await _get_repo().update(user.tenant_id, eid, body.model_dump())
    if not d: raise HTTPException(404, "Employee not found")
    return d


@router.delete("/{eid}", status_code=204)
async def delete_employee(eid: str, user: UserDep):
    await _get_repo().delete(user.tenant_id, eid)
