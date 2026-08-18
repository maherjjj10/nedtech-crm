"""Suppliers module."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository, new_id, utcnow_iso


router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[
        Depends(module_gate("crm")),
        Depends(require_permission("crm")),
    ],
)


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    vat_number: Optional[str] = None
    kvk_number: Optional[str] = None

    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Netherlands"

    iban: Optional[str] = None
    website: Optional[str] = None

    status: str = "active"
    notes: Optional[str] = None


class SupplierPatch(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    vat_number: Optional[str] = None
    kvk_number: Optional[str] = None

    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    iban: Optional[str] = None
    website: Optional[str] = None

    status: Optional[str] = None
    notes: Optional[str] = None


_repo: BaseRepository | None = None


def _get_repo() -> BaseRepository:
    global _repo

    if _repo is None:
        _repo = BaseRepository(
            get_db(),
            SupplierIn,
            "suppliers",
        )

    return _repo


@router.get("")
async def list_suppliers(
    user: UserDep,
    q: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    limit: int = 100,
    skip: int = 0,
):
    filters: dict = {}

    if q:
        filters["$or"] = [
            {
                "name": {
                    "$regex": q,
                    "$options": "i",
                }
            },
            {
                "company": {
                    "$regex": q,
                    "$options": "i",
                }
            },
            {
                "email": {
                    "$regex": q,
                    "$options": "i",
                }
            },
            {
                "vat_number": {
                    "$regex": q,
                    "$options": "i",
                }
            },
        ]

    if status_:
        filters["status"] = status_

    return await _get_repo().list(
        user.tenant_id,
        filters,
        limit=limit,
        skip=skip,
    )


@router.post("", status_code=201)
async def create_supplier(
    body: SupplierIn,
    user: UserDep,
):
    created = await _get_repo().create(
        user.tenant_id,
        body.model_dump(),
    )

    await get_db().activities.insert_one(
        {
            "_id": new_id(),
            "id": new_id(),
            "tenant_id": user.tenant_id,
            "type": "supplier_created",
            "entity_id": created["id"],
            "message": f"Supplier '{created['name']}' created",
            "actor": user.email,
            "created_at": utcnow_iso(),
        }
    )

    return created


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    user: UserDep,
):
    supplier = await _get_repo().get(
        user.tenant_id,
        supplier_id,
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return supplier


@router.patch("/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    body: SupplierPatch,
    user: UserDep,
):
    supplier = await _get_repo().update(
        user.tenant_id,
        supplier_id,
        body.model_dump(exclude_unset=True),
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return supplier


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: str,
    user: UserDep,
):
    ok = await _get_repo().delete(
        user.tenant_id,
        supplier_id,
    )

    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return None