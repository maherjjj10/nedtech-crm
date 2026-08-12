"""Clients module."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository, new_id, utcnow_iso


router = APIRouter(
    prefix="/clients",
    tags=["Clients"],
    dependencies=[
        Depends(module_gate("crm")),
        Depends(require_permission("crm")),
    ],
)


class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    contact_person: Optional[str] = None
    vat_number: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    status: str = "active"  # active | inactive | prospect
    notes: Optional[str] = None


class ClientPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    contact_person: Optional[str] = None
    vat_number: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    notes: Optional[str] = None


_repo: BaseRepository | None = None


def _get_repo() -> BaseRepository:
    global _repo

    if _repo is None:
        _repo = BaseRepository(
            get_db(),
            ClientIn,
            "clients",
        )

    return _repo


@router.get("")
async def list_clients(
    user: UserDep,
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
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
                "email": {
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
        ]

    if tag:
        filters["tags"] = tag

    if status_:
        filters["status"] = status_

    return await _get_repo().list(
        user.tenant_id,
        filters,
        limit=limit,
        skip=skip,
    )


@router.post("", status_code=201)
async def create_client(
    body: ClientIn,
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
            "type": "client_created",
            "entity_id": created["id"],
            "message": f"Client '{created['name']}' created",
            "actor": user.email,
            "created_at": utcnow_iso(),
        }
    )

    return created


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    user: UserDep,
):
    client = await _get_repo().get(
        user.tenant_id,
        client_id,
    )

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found",
        )

    return client


@router.patch("/{client_id}")
async def update_client(
    client_id: str,
    body: ClientPatch,
    user: UserDep,
):
    client = await _get_repo().update(
        user.tenant_id,
        client_id,
        body.model_dump(exclude_unset=True),
    )

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found",
        )

    return client


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: str,
    user: UserDep,
):
    ok = await _get_repo().delete(
        user.tenant_id,
        client_id,
    )

    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Client not found",
        )

    return None