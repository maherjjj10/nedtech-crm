"""Idempotent seed for the immutable Platform Owner.

Runs on backend startup. Contract:
  - PLATFORM_OWNER_EMAIL from env is the ONE and only platform_owner.
  - If that user does not exist: create it with a fresh personal workspace
    and the bootstrap password. Set protected=True.
  - If it exists: promote to platform_role='platform_owner', set protected=True,
    and — only if the user has no set password yet — set the bootstrap password.
"""
import logging
import os
import secrets

from app.core.database import get_db
from app.core.repository import new_id, utcnow_iso
from app.core.security import hash_password

logger = logging.getLogger(__name__)


DEFAULT_MODULES = {
    "crm": True, "sales": True, "tasks": True, "finance": True,
    "products": True, "hr": True, "files": True, "calendar": True,
    "reports": True, "ai": True, "settings": True,
    "inventory": False, "pos": False, "orders": False, "marketing": False,
    "website": False, "portal": False, "accounting": False, "payroll": False,
}


async def seed_platform_owner() -> None:
    email = (os.environ.get("PLATFORM_OWNER_EMAIL") or "").strip().lower()
    if not email:
        logger.info("No PLATFORM_OWNER_EMAIL set — skipping platform owner seed.")
        return
    name = os.environ.get("PLATFORM_OWNER_NAME") or email.split("@")[0].title()
    bootstrap_pw = os.environ.get("PLATFORM_OWNER_BOOTSTRAP_PASSWORD") or ""

    db = get_db()

    # First, ensure any pre-existing platform_owner that isn't this email is cleared,
    # so there is exactly one platform_owner globally.
    await db.users.update_many(
        {"platform_role": "platform_owner", "email": {"$ne": email}},
        {"$set": {"platform_role": None, "updated_at": utcnow_iso()}},
    )

    existing = await db.users.find_one({"email": email})
    if existing:
        patch = {
            "platform_role": "platform_owner",
            "protected": True,
            "updated_at": utcnow_iso(),
        }
        # Only seed the bootstrap password on FIRST bootstrap. Once the owner has
        # rotated their password via /profile/change-password, the seed must not
        # clobber it — env is the source of truth for the initial credential only.
        if bootstrap_pw and not existing.get("password_manually_set"):
            patch["password_hash"] = hash_password(bootstrap_pw)
        await db.users.update_one({"id": existing["id"]}, {"$set": patch})
        logger.info("Platform owner promoted: %s", email)
        return

    # Create a personal workspace for the owner and seed the account.
    tenant_id = new_id()
    slug = f"platform-{secrets.token_hex(3)}"
    tenant = {
        "_id": tenant_id, "id": tenant_id,
        "name": f"{name} Workspace", "slug": slug,
        "currency": "USD", "vat_rate": 0.0, "locale": "en",
        "modules": DEFAULT_MODULES.copy(),
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.tenants.insert_one(tenant)

    user_id = new_id()
    pw = bootstrap_pw or secrets.token_urlsafe(24)
    user = {
        "_id": user_id, "id": user_id,
        "email": email, "name": name,
        "tenant_id": tenant_id,
        "role": "admin",
        "platform_role": "platform_owner",
        "protected": True,
        "password_hash": hash_password(pw),
        "google_sub": None,
        "avatar_url": None,
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.users.insert_one(user)
    logger.info("Platform owner created: %s (bootstrap password shown in server logs once)", email)
