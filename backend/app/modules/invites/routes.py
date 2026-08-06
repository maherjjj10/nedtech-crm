"""Team invitations: owner invites teammates by email + role.

Endpoints (under /api/v1):
  POST   /tenants/me/invites             — create invite (auth: owner/admin)
  GET    /tenants/me/invites             — list pending invites
  DELETE /tenants/me/invites/{id}        — revoke
  GET    /invites/{token}                — public: preview invite
  POST   /invites/{token}/accept         — public: accept + create user
"""
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.email import send_html_email
from app.core.repository import new_id, utcnow_iso
from app.core.security import create_access_token, hash_password

router = APIRouter(tags=["Team Invites"])

INVITE_BASE_URL = os.environ.get("INVITE_BASE_URL", "http://localhost:3000")


class InviteIn(BaseModel):
    email: EmailStr
    role: str = "member"  # admin | manager | member
    name: str | None = None


class InviteAccept(BaseModel):
    password: str
    name: str | None = None


def _invite_url(token: str) -> str:
    return f"{INVITE_BASE_URL.rstrip('/')}/invite/{token}"


def _invite_html(*, inviter: str, tenant: str, role: str, url: str) -> str:
    return f"""
<!DOCTYPE html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f7f7f7;padding:24px;color:#0a0a0a">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:32px">
    <tr><td>
      <div style="font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:#666">NED Tech CRM</div>
      <h1 style="font-size:22px;margin:8px 0 16px 0;font-weight:800">You&apos;re invited to {tenant}</h1>
      <p style="font-size:14px;line-height:1.6;color:#333">
        {inviter} invited you to join <b>{tenant}</b> on NED Tech CRM as <b>{role}</b>.
      </p>
      <p style="margin:24px 0">
        <a href="{url}" style="background:#0a0a0a;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">Accept invitation</a>
      </p>
      <p style="font-size:12px;color:#888">Or paste this link into your browser:<br><span style="color:#333">{url}</span></p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="font-size:11px;color:#999">If you didn&apos;t expect this, you can safely ignore this email.</p>
    </td></tr>
  </table>
</body></html>
""".strip()


@router.post("/tenants/me/invites", status_code=201)
async def create_invite(body: InviteIn, user: UserDep):
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can invite")
    db = get_db()
    # If email already exists in this tenant → block
    existing_user = await db.users.find_one({"email": body.email.lower(), "tenant_id": user.tenant_id})
    if existing_user:
        raise HTTPException(409, "This email is already a member of your workspace")
    # Idempotency: overwrite prior pending invite for same email
    token = secrets.token_urlsafe(24)
    tenant = await db.tenants.find_one({"id": user.tenant_id}, {"_id": 0}) or {}
    inv = {
        "_id": new_id(), "id": new_id(),
        "tenant_id": user.tenant_id, "email": body.email.lower(),
        "role": body.role, "name": body.name,
        "token": token, "status": "pending",
        "invited_by": user.email, "invited_by_name": user.email,
        "created_at": utcnow_iso(), "expires_at": None,
    }
    await db.invites.update_one(
        {"tenant_id": user.tenant_id, "email": body.email.lower(), "status": "pending"},
        {"$set": inv}, upsert=True,
    )
    url = _invite_url(token)
    send_result = await send_html_email(
        to=body.email,
        subject=f"You're invited to {tenant.get('name', 'our workspace')} on NED Tech CRM",
        html=_invite_html(inviter=user.email, tenant=tenant.get("name", "our workspace"), role=body.role, url=url),
    )
    return {"invite": {**inv, "invite_url": url}, "email": send_result}


@router.get("/tenants/me/invites")
async def list_invites(user: UserDep):
    cur = get_db().invites.find({"tenant_id": user.tenant_id, "status": "pending"}, {"_id": 0}).sort([("created_at", -1)])
    invites = await cur.to_list(length=200)
    for i in invites:
        i["invite_url"] = _invite_url(i["token"])
    return invites


@router.delete("/tenants/me/invites/{invite_id}", status_code=204)
async def revoke_invite(invite_id: str, user: UserDep):
    await get_db().invites.update_one(
        {"id": invite_id, "tenant_id": user.tenant_id},
        {"$set": {"status": "revoked", "updated_at": utcnow_iso()}},
    )


@router.get("/invites/{token}")
async def preview_invite(token: str):
    db = get_db()
    inv = await db.invites.find_one({"token": token, "status": "pending"}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Invitation not found or already used")
    tenant = await db.tenants.find_one({"id": inv["tenant_id"]}, {"_id": 0, "modules": 0}) or {}
    return {"email": inv["email"], "role": inv["role"], "tenant_name": tenant.get("name"),
            "invited_by": inv.get("invited_by"), "created_at": inv.get("created_at")}


@router.post("/invites/{token}/accept")
async def accept_invite(token: str, body: InviteAccept):
    db = get_db()
    inv = await db.invites.find_one({"token": token, "status": "pending"})
    if not inv:
        raise HTTPException(404, "Invitation not found or already used")
    email = inv["email"]
    # If user with same email already exists → block (we don't cross-link accounts silently)
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(409, "An account with this email already exists — please sign in first")

    user_id = new_id()
    user_doc = {
        "_id": user_id, "id": user_id,
        "email": email, "name": body.name or inv.get("name") or email,
        "tenant_id": inv["tenant_id"], "role": inv.get("role", "member"),
        "password_hash": hash_password(body.password),
        "google_sub": None,
        "avatar_url": None,
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.users.insert_one(user_doc)
    await db.invites.update_one({"id": inv["id"]}, {"$set": {"status": "accepted", "accepted_at": utcnow_iso()}})

    token_jwt = create_access_token({
        "sub": user_id, "tenant_id": inv["tenant_id"],
        "email": email, "role": user_doc["role"],
    })
    tenant = await db.tenants.find_one({"id": inv["tenant_id"]}, {"_id": 0}) or {}
    return {"access_token": token_jwt, "token_type": "bearer",
            "user": {k: v for k, v in user_doc.items() if k not in ("_id", "password_hash")},
            "tenant": tenant}
