"""Auth module: register, login, google oauth, /me."""
from datetime import datetime, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserDep
from app.core.repository import new_id, utcnow_iso
from app.core.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    company_name: str = Field(min_length=1, max_length=120)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    tenant: dict


DEFAULT_MODULES = {
    "crm": True, "sales": True, "tasks": True, "finance": True,
    "products": True, "hr": True, "files": True, "calendar": True,
    "reports": True, "ai": True, "settings": True,
    # Future
    "inventory": False, "pos": False, "orders": False, "marketing": False,
    "website": False, "portal": False, "accounting": False, "payroll": False,
}


async def _create_tenant_and_owner(email: str, name: str, company: str, password_hash: Optional[str], google_sub: Optional[str] = None) -> tuple[dict, dict]:
    db = get_db()
    tenant_id = new_id()
    slug_base = company.lower().replace(" ", "-")[:40] or "workspace"
    slug = f"{slug_base}-{secrets.token_hex(3)}"
    tenant = {
        "_id": tenant_id, "id": tenant_id,
        "name": company, "slug": slug,
        "currency": "USD", "vat_rate": 0.0, "locale": "en",
        "modules": DEFAULT_MODULES.copy(),
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.tenants.insert_one(tenant)

    user_id = new_id()
    user = {
        "_id": user_id, "id": user_id,
        "email": email.lower(), "name": name,
        "tenant_id": tenant_id, "role": "owner",
        "password_hash": password_hash,
        "google_sub": google_sub,
        "avatar_url": None,
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.users.insert_one(user)
    return user, tenant


def _serialize(doc: dict) -> dict:
    d = {k: v for k, v in doc.items() if k not in ("_id", "password_hash")}
    return d


def _token_for(user: dict, impersonating_from: str | None = None, original_tenant_id: str | None = None) -> str:
    payload = {
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "role": user.get("role", "member"),
        "platform_role": user.get("platform_role"),
    }
    if impersonating_from:
        payload["impersonating_from"] = impersonating_from
        payload["original_tenant_id"] = original_tenant_id
    return create_access_token(payload)


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterInput):
    db = get_db()
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user, tenant = await _create_tenant_and_owner(
        body.email, body.name, body.company_name, hash_password(body.password)
    )
    return TokenResponse(access_token=_token_for(user), user=_serialize(user), tenant=_serialize(tenant))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginInput):
    db = get_db()
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    tenant = await db.tenants.find_one({"id": user["tenant_id"]})
    return TokenResponse(access_token=_token_for(user), user=_serialize(user), tenant=_serialize(tenant))


@router.get("/me")
async def me(user: UserDep):
    db = get_db()
    u = await db.users.find_one({"id": user.user_id})
    t = await db.tenants.find_one({"id": user.tenant_id})
    if not u or not t:
        raise HTTPException(404, "User or tenant not found")
    payload = {"user": _serialize(u), "tenant": _serialize(t)}
    # Surface impersonation context so the frontend can show the banner
    if user.is_impersonating:
        payload["user"]["impersonating_from"] = user.impersonating_from
        payload["user"]["original_tenant_id"] = user.original_tenant_id
    return payload


# ---------- Google OAuth (works when GOOGLE_CLIENT_ID/SECRET are configured) ----------
from authlib.integrations.starlette_client import OAuth  # noqa: E402

_oauth = OAuth()
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    _oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/google/login")
async def google_login(request: Request):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_callback"))
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    try:
        token = await _oauth.google.authorize_access_token(request)
        info = token.get("userinfo") or {}
    except Exception:
        raise HTTPException(400, "Google authentication failed")

    db = get_db()
    user = await db.users.find_one({"google_sub": info["sub"]}) if info.get("sub") else None
    if not user and info.get("email"):
        user = await db.users.find_one({"email": info["email"].lower()})
        if user and info.get("email_verified"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"google_sub": info["sub"]}})
    if not user:
        if not info.get("email"):
            raise HTTPException(400, "Google did not return an email")
        user, _tenant = await _create_tenant_and_owner(
            info["email"], info.get("name") or info["email"], f"{info.get('name') or 'My'} Workspace", None, info["sub"]
        )
    jwt_token = _token_for(user)
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}")
