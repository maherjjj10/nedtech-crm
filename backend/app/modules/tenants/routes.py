"""Tenants module: workspace info + module toggles."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.repository import utcnow_iso

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class TenantUpdate(BaseModel):
    name: str | None = None
    currency: str | None = None
    vat_rate: float | None = None
    locale: str | None = None
    logo_url: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None


class ModuleToggle(BaseModel):
    module: str
    enabled: bool


@router.get("/me")
async def get_my_tenant(user: UserDep):
    t = await get_db().tenants.find_one({"id": user.tenant_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Tenant not found")
    return t


@router.patch("/me")
async def update_my_tenant(body: TenantUpdate, user: UserDep):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        return await get_my_tenant(user)
    patch["updated_at"] = utcnow_iso()
    await get_db().tenants.update_one({"id": user.tenant_id}, {"$set": patch})
    return await get_my_tenant(user)


@router.post("/me/modules")
async def toggle_module(body: ModuleToggle, user: UserDep):
    await get_db().tenants.update_one(
        {"id": user.tenant_id},
        {"$set": {f"modules.{body.module}": body.enabled, "updated_at": utcnow_iso()}},
    )
    return await get_my_tenant(user)
