"""Auth module: register, login, google oauth, /me, forgot/reset password."""
from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserDep
from app.core.email import send_html_email
from app.core.repository import new_id, utcnow_iso
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.sessions.routes import register_session

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


def _token_for(user: dict, jti: str | None = None,
               impersonating_from: str | None = None,
               original_tenant_id: str | None = None) -> str:
    payload = {
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "role": user.get("role", "member"),
        "platform_role": user.get("platform_role"),
    }
    if jti:
        payload["jti"] = jti
    if impersonating_from:
        payload["impersonating_from"] = impersonating_from
        payload["original_tenant_id"] = original_tenant_id
    return create_access_token(payload)


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterInput, request: Request):
    db = get_db()
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user, tenant = await _create_tenant_and_owner(
        email, body.name, body.company_name, hash_password(body.password)
    )
    jti = new_id()
    await register_session(
        session_id=jti, user_id=user["id"], tenant_id=user["tenant_id"],
        request=request, ttl_minutes=settings.JWT_EXPIRE_MINUTES,
    )
    return TokenResponse(access_token=_token_for(user, jti=jti), user=_serialize(user), tenant=_serialize(tenant))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginInput, request: Request):
    db = get_db()
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    tenant = await db.tenants.find_one({"id": user["tenant_id"]})
    jti = new_id()
    await register_session(
        session_id=jti, user_id=user["id"], tenant_id=user["tenant_id"],
        request=request, ttl_minutes=settings.JWT_EXPIRE_MINUTES,
    )
    return TokenResponse(access_token=_token_for(user, jti=jti), user=_serialize(user), tenant=_serialize(tenant))


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


# ---------- Forgot / Reset password ----------

class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


def _hash_reset_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _reset_email_html(*, url: str, name: str) -> str:
    return f"""
<!DOCTYPE html><html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f7f7f7;padding:24px;color:#0a0a0a">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:32px">
    <tr><td>
      <div style="font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:#666">NED Tech CRM</div>
      <h1 style="font-size:22px;margin:8px 0 16px 0;font-weight:800">Reset your password</h1>
      <p style="font-size:14px;line-height:1.6;color:#333">Hi {name}, we received a request to reset your NED Tech CRM password. This link is valid for 1 hour and can be used only once.</p>
      <p style="margin:24px 0">
        <a href="{url}" style="background:#0a0a0a;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">Reset password</a>
      </p>
      <p style="font-size:12px;color:#888">Or paste this link into your browser:<br><span style="color:#333">{url}</span></p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="font-size:11px;color:#999">If you didn&apos;t request this, you can safely ignore this email — your password won&apos;t change.</p>
    </td></tr>
  </table>
</body></html>
""".strip()


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordIn):
    """Always returns 200 to prevent email enumeration."""
    db = get_db()
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    result = {"ok": True, "message": "If that email exists, a reset link has been sent."}
    if not user:
        return result

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)
    now = datetime.now(timezone.utc)
    await db.password_reset_tokens.insert_one({
        "_id": new_id(),
        "user_id": user["id"], "email": email,
        "token_hash": token_hash,
        "expires_at": now + timedelta(hours=1),
        "used_at": None,
        "created_at": now.isoformat(),
    })
    reset_url = f"{(settings.FRONTEND_URL or '').rstrip('/')}/auth/reset-password/{raw_token}"
    send_result = await send_html_email(
        to=email,
        subject="Reset your NED Tech CRM password",
        html=_reset_email_html(url=reset_url, name=user.get("name") or email),
    )
    # Surface the link ONLY when email isn't configured — never in production paths.
    if not send_result.get("sent"):
        result["dev_reset_url"] = reset_url
    return result


@router.post("/reset-password")
async def reset_password(body: ResetPasswordIn):
    db = get_db()
    token_hash = _hash_reset_token(body.token)
    doc = await db.password_reset_tokens.find_one({"token_hash": token_hash})
    if not doc:
        raise HTTPException(400, "Invalid or expired reset link")
    if doc.get("used_at"):
        raise HTTPException(400, "This reset link has already been used")
    exp = doc.get("expires_at")
    if exp:
        exp_dt = exp if isinstance(exp, datetime) else datetime.fromisoformat(str(exp))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp_dt:
            raise HTTPException(400, "This reset link has expired")

    # Update password AND revoke all existing sessions for that user.
    await db.users.update_one(
        {"id": doc["user_id"]},
        {"$set": {
            "password_hash": hash_password(body.new_password),
            "password_manually_set": True,
            "password_updated_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
        }},
    )
    await db.sessions.update_many(
        {"user_id": doc["user_id"], "revoked_at": None},
        {"$set": {"revoked_at": utcnow_iso()}},
    )
    await db.password_reset_tokens.update_one(
        {"_id": doc["_id"]},
        {"$set": {"used_at": utcnow_iso()}},
    )
    return {"ok": True, "message": "Password reset. Please sign in with your new password."}


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
