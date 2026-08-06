"""Platform administration — cross-tenant super-admin surface.

Endpoints (all require platform_role):
  GET   /platform/tenants                 — list all tenants + user counts
  GET   /platform/tenants/{tid}           — tenant detail
  GET   /platform/tenants/{tid}/users     — users in a tenant
  GET   /platform/users                   — global user search
  PATCH /platform/users/{uid}/role        — set platform_role or tenant_role
  DELETE /platform/users/{uid}            — delete user (blocked for protected)
  POST  /platform/impersonate             — start impersonation (returns new JWT)
  POST  /platform/audit                   — list recent audit events
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep, CurrentUser, require_platform_role
from app.core.repository import new_id, utcnow_iso
from app.core.roles import (
    PLATFORM_ROLES, TENANT_ROLES, RANK, normalize_tenant_role, effective_rank,
)
from app.core.security import create_access_token

router = APIRouter(prefix="/platform", tags=["Platform Admin"])

# All platform routes require at least super_admin
_gate = Depends(require_platform_role("super_admin"))


async def _audit(action: str, actor: UserDep, target_tenant: str | None = None,
                 target_user: str | None = None, meta: dict | None = None):
    await get_db().platform_audit.insert_one({
        "_id": new_id(), "id": new_id(),
        "actor_user_id": actor.user_id, "actor_email": actor.email,
        "actor_platform_role": actor.platform_role,
        "action": action, "target_tenant": target_tenant, "target_user": target_user,
        "meta": meta or {}, "created_at": utcnow_iso(),
    })


def _pub(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("_id", "password_hash")}


# --------------------------- TENANTS ---------------------------

@router.get("/tenants", dependencies=[_gate])
async def list_tenants(user: UserDep):
    db = get_db()
    tenants = await db.tenants.find({}, {"_id": 0}).sort([("created_at", -1)]).to_list(length=1000)
    # Attach user count + plan
    for t in tenants:
        t["user_count"] = await db.users.count_documents({"tenant_id": t["id"]})
        billing = await db.billing.find_one({"tenant_id": t["id"]}, {"_id": 0})
        t["billing"] = billing or {"plan": None, "status": "free"}
    return tenants


@router.get("/tenants/{tid}", dependencies=[_gate])
async def get_tenant(tid: str):
    t = await get_db().tenants.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Tenant not found")
    return t


@router.get("/tenants/{tid}/users", dependencies=[_gate])
async def tenant_users(tid: str):
    cur = get_db().users.find({"tenant_id": tid}).sort([("created_at", -1)])
    return [_pub(u) for u in await cur.to_list(length=500)]


# --------------------------- USERS -----------------------------

@router.get("/users", dependencies=[_gate])
async def search_users(q: str | None = None, limit: int = 50):
    query = {}
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]
    cur = get_db().users.find(query).sort([("created_at", -1)]).limit(limit)
    return [_pub(u) for u in await cur.to_list(length=limit)]


class RoleUpdate(BaseModel):
    platform_role: str | None = None    # None to clear, or one of PLATFORM_ROLES
    tenant_role: str | None = None      # or one of TENANT_ROLES


@router.patch("/users/{uid}/role")
async def set_role(uid: str, body: RoleUpdate, user: CurrentUser = Depends(require_platform_role("super_admin"))):
    db = get_db()
    target = await db.users.find_one({"id": uid})
    if not target:
        raise HTTPException(404, "User not found")

    # Immutability guards
    if target.get("protected") or target.get("platform_role") == "platform_owner":
        raise HTTPException(403, "This account is protected and cannot be modified")

    # Cannot grant a role above your own
    tgt_platform = body.platform_role if body.platform_role is not None else target.get("platform_role")
    tgt_tenant = normalize_tenant_role(body.tenant_role) if body.tenant_role is not None else target.get("role")
    if effective_rank(user.platform_role, user.role) < effective_rank(tgt_platform, tgt_tenant):
        raise HTTPException(403, "Cannot grant a role above your own")

    patch = {"updated_at": utcnow_iso()}
    if body.platform_role is not None:
        if body.platform_role != "" and body.platform_role not in PLATFORM_ROLES:
            raise HTTPException(400, "Invalid platform_role")
        # Only platform_owner may grant super_admin
        if body.platform_role == "super_admin" and not user.is_platform_owner:
            raise HTTPException(403, "Only platform_owner may grant super_admin")
        if body.platform_role == "platform_owner":
            raise HTTPException(403, "There can be only one platform_owner (protected)")
        patch["platform_role"] = body.platform_role or None
    if body.tenant_role is not None:
        norm = normalize_tenant_role(body.tenant_role)
        if norm not in TENANT_ROLES:
            raise HTTPException(400, "Invalid tenant_role")
        patch["role"] = norm

    await db.users.update_one({"id": uid}, {"$set": patch})
    await _audit("user.role_change", user, target_tenant=target.get("tenant_id"),
                 target_user=uid, meta={"before": {"platform_role": target.get("platform_role"), "role": target.get("role")}, "after": patch})
    fresh = await db.users.find_one({"id": uid})
    return _pub(fresh)


@router.delete("/users/{uid}", status_code=204)
async def delete_user(uid: str, user: CurrentUser = Depends(require_platform_role("super_admin"))):
    db = get_db()
    target = await db.users.find_one({"id": uid})
    if not target:
        raise HTTPException(404, "User not found")
    if target.get("protected") or target.get("platform_role") == "platform_owner":
        raise HTTPException(403, "This account is protected and cannot be deleted")
    if effective_rank(user.platform_role, user.role) < effective_rank(target.get("platform_role"), target.get("role")):
        raise HTTPException(403, "Cannot delete a user with a higher role than yours")
    await db.users.delete_one({"id": uid})
    await _audit("user.delete", user, target_tenant=target.get("tenant_id"), target_user=uid,
                 meta={"email": target.get("email")})


# --------------------------- IMPERSONATION ---------------------

class ImpersonateIn(BaseModel):
    tenant_id: str
    reason: str | None = "support"


@router.post("/impersonate")
async def impersonate(body: ImpersonateIn, user: CurrentUser = Depends(require_platform_role("super_admin"))):
    if user.is_impersonating:
        raise HTTPException(400, "Already impersonating — exit first")
    db = get_db()
    tenant = await db.tenants.find_one({"id": body.tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # Ephemeral principal — original identity preserved via impersonating_from claim.
    # NO writes to the users collection; NO tenant reassignment on the real user.
    original_user = await db.users.find_one({"id": user.user_id})
    ephemeral = {
        "id": original_user["id"], "email": original_user["email"],
        "tenant_id": body.tenant_id, "role": "admin",  # act as tenant admin inside the workspace
        "platform_role": original_user.get("platform_role"),
    }
    token = create_access_token({
        "sub": ephemeral["id"], "tenant_id": ephemeral["tenant_id"],
        "email": ephemeral["email"], "role": ephemeral["role"],
        "platform_role": ephemeral["platform_role"],
        "impersonating_from": user.user_id,
        "original_tenant_id": original_user["tenant_id"],
    })
    await _audit("impersonation.start", user, target_tenant=body.tenant_id,
                 meta={"tenant_name": tenant.get("name"), "reason": body.reason})
    return {"access_token": token, "token_type": "bearer",
            "tenant": tenant,
            "note": "All actions taken while impersonating are logged with your original identity."}


@router.post("/impersonate/stop")
async def stop_impersonation(user: UserDep):
    if not user.is_impersonating:
        raise HTTPException(400, "Not currently impersonating")
    db = get_db()
    original = await db.users.find_one({"id": user.impersonating_from})
    if not original:
        raise HTTPException(404, "Original user not found")
    tenant = await db.tenants.find_one({"id": original["tenant_id"]}, {"_id": 0}) or {}
    token = create_access_token({
        "sub": original["id"], "tenant_id": original["tenant_id"],
        "email": original["email"], "role": original.get("role"),
        "platform_role": original.get("platform_role"),
    })
    await _audit("impersonation.stop", user, target_tenant=user.tenant_id)
    return {"access_token": token, "token_type": "bearer",
            "user": {k: v for k, v in original.items() if k not in ("_id", "password_hash")},
            "tenant": tenant}


# --------------------------- AUDIT LOG -------------------------

@router.get("/audit", dependencies=[_gate])
async def audit_log(limit: int = 100):
    cur = get_db().platform_audit.find({}, {"_id": 0}).sort([("created_at", -1)]).limit(limit)
    return await cur.to_list(length=limit)
