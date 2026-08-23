"""Team invitations: owner/admin invites teammates by email + role + permissions."""

import os
import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.email import send_html_email
from app.core.repository import new_id, utcnow_iso
from app.core.roles import (
    TENANT_ROLES,
    default_permissions,
    normalize_permissions,
    normalize_tenant_role,
)
from app.core.security import create_access_token, hash_password


router = APIRouter(tags=["Team Invites"])


INVITE_BASE_URL = (
    os.environ.get("INVITE_BASE_URL")
    or os.environ.get("FRONTEND_URL")
    or "http://localhost:3000"
).rstrip("/")


# ============================================================
# Schemas
# ============================================================


class InviteIn(BaseModel):
    email: EmailStr
    role: str = "employee"
    name: str | None = None
    permissions: dict[str, bool] | None = None


class InviteAccept(BaseModel):
    password: str
    name: str | None = None


# ============================================================
# Helpers
# ============================================================


def _invite_url(token: str) -> str:
    return f"{INVITE_BASE_URL.rstrip('/')}/invite/{token}"


def _invite_html(
    *,
    inviter: str,
    tenant: str,
    role: str,
    url: str,
) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        padding:40px;
        background:#f5f5f5;
        font-family:Arial,Helvetica,sans-serif;
    ">
        <div style="
            max-width:600px;
            margin:auto;
            background:white;
            padding:40px;
            border-radius:12px;
        ">
            <h2>You have been invited to {tenant}</h2>

            <p>
                <strong>{inviter}</strong> invited you to join
                <strong>{tenant}</strong> on NED Tech CRM.
            </p>

            <p>
                Your role:
                <strong>{role}</strong>
            </p>

            <p style="margin-top:30px;">
                <a
                    href="{url}"
                    style="
                        display:inline-block;
                        padding:12px 22px;
                        background:#111;
                        color:#fff;
                        text-decoration:none;
                        border-radius:8px;
                    "
                >
                    Accept Invitation
                </a>
            </p>

            <p style="
                margin-top:30px;
                color:#777;
                font-size:13px;
            ">
                If you did not expect this invitation, you can safely ignore
                this email.
            </p>
        </div>
    </body>
    </html>
    """


def _validate_role(role: str) -> str:
    """
    Normalize legacy roles and make sure the invitation
    uses one of the supported tenant roles.
    """

    normalized = normalize_tenant_role(role)

    if normalized not in TENANT_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid role. Allowed roles: "
                "admin, manager, employee, viewer"
            ),
        )

    return normalized


# ============================================================
# Create invitation
# ============================================================


@router.post("/tenants/me/invites", status_code=201)
async def create_invite(
    body: InviteIn,
    user: UserDep,
):
    """
    Create a team invitation.

    Only workspace admins/owners can invite users.

    The invitation stores:
    - role
    - permissions
    - name
    - email
    """

    # --------------------------------------------------------
    # Permission to invite
    # --------------------------------------------------------

    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only owners and admins can invite team members",
        )

    # --------------------------------------------------------
    # Normalize role
    # --------------------------------------------------------

    role = _validate_role(body.role)

    # --------------------------------------------------------
    # Prevent admin from creating a higher privilege account
    # --------------------------------------------------------

    if user.role == "admin" and role == "admin":
        # Existing behavior allows admins to invite.
        # Keep this compatible with the current system.
        pass

    # --------------------------------------------------------
    # Normalize permissions
    # --------------------------------------------------------

    permissions = normalize_permissions(body.permissions)

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    db = get_db()

    email = body.email.lower()

    # --------------------------------------------------------
    # Check if user already exists in this tenant
    # --------------------------------------------------------

    existing_user = await db.users.find_one(
        {
            "email": email,
            "tenant_id": user.tenant_id,
        }
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="This email is already a member of your workspace",
        )

    # --------------------------------------------------------
    # Generate invitation
    # --------------------------------------------------------

    token = secrets.token_urlsafe(24)

    tenant = await db.tenants.find_one(
        {"id": user.tenant_id},
        {"_id": 0},
    ) or {}

    invite_id = new_id()

    inv = {
        "_id": invite_id,
        "id": invite_id,

        "tenant_id": user.tenant_id,

        "email": email,
        "name": body.name,

        "role": role,
        "permissions": permissions,

        "token": token,
        "status": "pending",

        "invited_by": user.email,
        "invited_by_name": user.email,

        "created_at": utcnow_iso(),
        "expires_at": None,
    }

    # --------------------------------------------------------
    # Replace previous pending invitation
    # --------------------------------------------------------

    await db.invites.update_one(
        {
            "tenant_id": user.tenant_id,
            "email": email,
            "status": "pending",
        },
        {
            "$set": inv,
        },
        upsert=True,
    )

        # --------------------------------------------------------
    # Send email
    # --------------------------------------------------------

    url = _invite_url(token)

    send_result = await send_html_email(
        to=email,
        subject=(
            f"You're invited to "
            f"{tenant.get('name', 'our workspace')} "
            f"on NED Tech CRM"
        ),
        html=_invite_html(
            inviter=user.email,
            tenant=tenant.get(
                "name",
                "our workspace",
            ),
            role=role,
            url=url,
        ),
        reply_to=tenant.get("email"),
    )

    # --------------------------------------------------------
    # Handle email failure
    # --------------------------------------------------------

    if not send_result.get("sent"):
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Invitation was created, "
                    "but the email could not be sent."
                ),
                "reason": send_result.get(
                    "reason",
                    "email_send_failed",
                ),
            },
        )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "invite": {
            **inv,
            "invite_url": url,
        },
        "email": send_result,
    }
    
    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "invite": {
            **inv,
            "invite_url": url,
        },
        "email": send_result,
    }


# ============================================================
# List pending invitations
# ============================================================


@router.get("/tenants/me/invites")
async def list_invites(
    user: UserDep,
):
    """
    List pending invitations for the current workspace.
    """

    cur = (
        get_db()
        .invites
        .find(
            {
                "tenant_id": user.tenant_id,
                "status": "pending",
            },
            {
                "_id": 0,
            },
        )
        .sort(
            [
                ("created_at", -1),
            ]
        )
    )

    invites = await cur.to_list(length=200)

    for invite in invites:
        invite["permissions"] = normalize_permissions(
            invite.get("permissions")
        )

        invite["invite_url"] = _invite_url(
            invite["token"]
        )

    return invites


# ============================================================
# Revoke invitation
# ============================================================


@router.delete(
    "/tenants/me/invites/{invite_id}",
    status_code=204,
)
async def revoke_invite(
    invite_id: str,
    user: UserDep,
):
    """
    Revoke a pending invitation.
    """

    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only owners and admins can revoke invitations",
        )

    await get_db().invites.update_one(
        {
            "id": invite_id,
            "tenant_id": user.tenant_id,
            "status": "pending",
        },
        {
            "$set": {
                "status": "revoked",
                "updated_at": utcnow_iso(),
            }
        },
    )


# ============================================================
# Public invitation preview
# ============================================================


@router.get("/invites/{token}")
async def preview_invite(
    token: str,
):
    """
    Public endpoint used by the invitation page.
    """

    db = get_db()

    inv = await db.invites.find_one(
        {
            "token": token,
            "status": "pending",
        },
        {
            "_id": 0,
        },
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found or already used",
        )

    tenant = await db.tenants.find_one(
        {
            "id": inv["tenant_id"],
        },
        {
            "_id": 0,
            "modules": 0,
        },
    ) or {}

    return {
        "email": inv["email"],
        "name": inv.get("name"),
        "role": normalize_tenant_role(
            inv.get("role", "employee")
        ),
        "permissions": normalize_permissions(
            inv.get("permissions")
        ),
        "tenant_name": tenant.get("name"),
        "invited_by": inv.get("invited_by"),
        "created_at": inv.get("created_at"),
    }


# ============================================================
# Accept invitation
# ============================================================


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str,
    body: InviteAccept,
):
    """
    Accept invitation and create the user's account.

    IMPORTANT:

    Accepting an invitation creates BOTH:

    1. Authentication user
    2. Employee profile

    The same permissions are copied to both records.
    """

    db = get_db()

    # --------------------------------------------------------
    # Find invitation
    # --------------------------------------------------------

    inv = await db.invites.find_one(
        {
            "token": token,
            "status": "pending",
        }
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found or already used",
        )

    # --------------------------------------------------------
    # Normalize role + permissions
    # --------------------------------------------------------

    role = _validate_role(
        inv.get("role", "employee")
    )

    permissions = normalize_permissions(
        inv.get("permissions")
    )

    email = inv["email"].lower()

    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    existing = await db.users.find_one(
        {
            "email": email,
        }
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email already exists. "
                "Please sign in first."
            ),
        )

    # --------------------------------------------------------
    # Create authentication user
    # --------------------------------------------------------

    user_id = new_id()

    user_name = (
        body.name
        or inv.get("name")
        or email
    )

    user_doc = {
        "_id": user_id,
        "id": user_id,

        "email": email,
        "name": user_name,

        "tenant_id": inv["tenant_id"],

        "role": role,

        # Individual module permissions
        "permissions": permissions,

        "password_hash": hash_password(
            body.password
        ),

        "google_sub": None,
        "avatar_url": None,

        "created_at": utcnow_iso(),
        "updated_at": utcnow_iso(),
    }

    await db.users.insert_one(user_doc)

    # --------------------------------------------------------
    # Create employee profile
    # --------------------------------------------------------
    #
    # The Employee record is intentionally separate from
    # the authentication User record.
    #
    # users:
    #   authentication
    #   password
    #   permissions
    #   tenant
    #
    # employees:
    #   HR/business profile
    #   department
    #   position
    #   salary
    #   status
    #
    # user_id creates the relationship between them.
    # --------------------------------------------------------

    employee_id = new_id()

    employee_doc = {
        "_id": employee_id,
        "id": employee_id,

        # Link employee to authentication account
        "user_id": user_id,

        "tenant_id": inv["tenant_id"],

        "name": user_name,
        "email": email,

        "phone": None,

        "role": role,

        "department": None,
        "position": None,

        "salary": 0,
        "currency": "USD",

        "hire_date": None,

        "status": "active",

        "avatar_url": None,

        # Keep the same permissions on the employee profile
        "permissions": permissions,

        "created_at": utcnow_iso(),
        "updated_at": utcnow_iso(),
    }

    await db.employees.insert_one(employee_doc)

    # --------------------------------------------------------
    # Mark invitation as accepted
    # --------------------------------------------------------

    await db.invites.update_one(
        {
            "id": inv["id"],
        },
        {
            "$set": {
                "status": "accepted",
                "accepted_at": utcnow_iso(),
            }
        },
    )

    # --------------------------------------------------------
    # Create login token
    # --------------------------------------------------------

    token_jwt = create_access_token(
        {
            "sub": user_id,
            "tenant_id": inv["tenant_id"],
            "email": email,
            "role": role,
        }
    )

    # --------------------------------------------------------
    # Tenant
    # --------------------------------------------------------

    tenant = await db.tenants.find_one(
        {
            "id": inv["tenant_id"],
        },
        {
            "_id": 0,
        },
    ) or {}

    # --------------------------------------------------------
    # Safe user response
    # --------------------------------------------------------

    safe_user = {
        key: value
        for key, value in user_doc.items()
        if key not in (
            "_id",
            "password_hash",
        )
    }

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "access_token": token_jwt,
        "token_type": "bearer",
        "user": safe_user,
        "employee": {
            key: value
            for key, value in employee_doc.items()
            if key != "_id"
        },
        "tenant": tenant,
    }