"""Tenants module: workspace information + module toggles."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep, require_tenant_role
from app.core.repository import utcnow_iso


router = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
)


# ============================================================
# Allowed tenant modules
# ============================================================

TENANT_MODULES = {
    "crm",
    "sales",
    "tasks",
    "finance",
    "products",
    "hr",
    "files",
    "calendar",
    "reports",
    "ai",
    "settings",
    "inventory",
    "pos",
    "orders",
    "marketing",
    "website",
    "portal",
    "accounting",
    "payroll",
}


# ============================================================
# Schemas
# ============================================================

class TenantUpdate(BaseModel):
    name: str | None = None
    currency: str | None = None
    vat_rate: float | None = None
    locale: str | None = None
    logo_url: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    iban: str | None = None
    kvk_number: str | None = None
    vat_number: str | None = None


class ModuleToggle(BaseModel):
    module: str
    enabled: bool


# ============================================================
# GET CURRENT TENANT
# ============================================================

@router.get("/me")
async def get_my_tenant(
    user: UserDep,
):
    tenant = await get_db().tenants.find_one(
        {
            "id": user.tenant_id,
        },
        {
            "_id": 0,
        },
    )

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    return tenant


# ============================================================
# UPDATE TENANT
# ADMIN ONLY
# ============================================================

@router.patch(
    "/me",
    dependencies=[
        Depends(require_tenant_role("admin"))
    ],
)
async def update_my_tenant(
    body: TenantUpdate,
    user: UserDep,
):
    patch = {
        key: value
        for key, value in body.model_dump().items()
        if value is not None
    }

    if not patch:
        return await get_my_tenant(user)

    patch["updated_at"] = utcnow_iso()

    result = await get_db().tenants.update_one(
        {
            "id": user.tenant_id,
        },
        {
            "$set": patch,
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    return await get_my_tenant(user)


# ============================================================
# TOGGLE MODULE
# ADMIN ONLY
# ============================================================

@router.post(
     "/me/modules",
    dependencies=[
        Depends(require_tenant_role("admin"))
    ],
)
async def toggle_module(
    body: ModuleToggle,
    user: UserDep,
):
    module = body.module.strip().lower()

    if module not in TENANT_MODULES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown module '{module}'.",
        )

    tenant = await get_db().tenants.find_one(
        {
            "id": user.tenant_id,
        },
        {
            "_id": 0,
        },
    )

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found",
        )

    await get_db().tenants.update_one(
        {
            "id": user.tenant_id,
        },
        {
            "$set": {
                f"modules.{module}": body.enabled,
                "updated_at": utcnow_iso(),
            }
        },
    )

    return await get_my_tenant(user)