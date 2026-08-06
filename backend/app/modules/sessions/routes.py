"""Session tracking + forgot/reset password.

We add a `jti` (session id) claim to every access token issued at login/register.
On each authenticated request the deps layer checks the jti is still active in
the `sessions` collection. Users can list their active sessions and revoke any
one (or all). This turns a stateless JWT into a revocable session without
changing the token format.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep, decode_current_token
from app.core.repository import new_id, utcnow_iso

router = APIRouter(prefix="/profile/sessions", tags=["Sessions"])


def _parse_ua(ua: str) -> str:
    if not ua:
        return "Unknown device"
    # Very light-touch UA parsing — no external dep.
    ua_low = ua.lower()
    device = "Desktop"
    if "mobile" in ua_low or "iphone" in ua_low or "android" in ua_low:
        device = "Mobile"
    elif "ipad" in ua_low or "tablet" in ua_low:
        device = "Tablet"
    if "chrome" in ua_low and "edg" not in ua_low: browser = "Chrome"
    elif "safari" in ua_low and "chrome" not in ua_low: browser = "Safari"
    elif "firefox" in ua_low: browser = "Firefox"
    elif "edg" in ua_low: browser = "Edge"
    else: browser = "Browser"
    return f"{browser} · {device}"


async def register_session(*, session_id: str, user_id: str, tenant_id: str,
                           request: Request, ttl_minutes: int) -> None:
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else None
    now = datetime.now(timezone.utc)
    await get_db().sessions.insert_one({
        "_id": session_id, "id": session_id,
        "user_id": user_id, "tenant_id": tenant_id,
        "user_agent": ua, "device": _parse_ua(ua),
        "ip": ip,
        "created_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
        "revoked_at": None,
    })


@router.get("")
async def list_sessions(user: UserDep, request: Request):
    """List all active sessions for the current user."""
    # Extract current jti from token
    _, claims = decode_current_token(request)
    current_jti = claims.get("jti")
    cur = get_db().sessions.find(
        {"user_id": user.user_id, "revoked_at": None},
        {"_id": 0, "user_agent": 0},
    ).sort([("last_seen_at", -1)])
    out = []
    for s in await cur.to_list(length=100):
        s["is_current"] = s.get("id") == current_jti
        out.append(s)
    return out


@router.delete("/{sid}", status_code=204)
async def revoke_session(sid: str, user: UserDep):
    r = await get_db().sessions.update_one(
        {"id": sid, "user_id": user.user_id, "revoked_at": None},
        {"$set": {"revoked_at": utcnow_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Session not found or already revoked")


@router.post("/revoke-others")
async def revoke_others(user: UserDep, request: Request):
    _, claims = decode_current_token(request)
    current_jti = claims.get("jti")
    r = await get_db().sessions.update_many(
        {"user_id": user.user_id, "revoked_at": None, "id": {"$ne": current_jti}},
        {"$set": {"revoked_at": utcnow_iso()}},
    )
    return {"revoked": r.modified_count}
