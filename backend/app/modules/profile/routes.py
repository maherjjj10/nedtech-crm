"""User profile: update own details, change password."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.repository import utcnow_iso
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfilePatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


@router.patch("/me")
async def update_profile(body: ProfilePatch, user: UserDep):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        return await get_db().users.find_one({"id": user.user_id}, {"_id": 0, "password_hash": 0})
    patch["updated_at"] = utcnow_iso()
    await get_db().users.update_one({"id": user.user_id}, {"$set": patch})
    return await get_db().users.find_one({"id": user.user_id}, {"_id": 0, "password_hash": 0})


@router.post("/change-password")
async def change_password(body: PasswordChange, user: UserDep):
    db = get_db()
    u = await db.users.find_one({"id": user.user_id})
    if not u or not u.get("password_hash"):
        raise HTTPException(400, "No password set on this account")
    if not verify_password(body.current_password, u["password_hash"]):
        raise HTTPException(401, "Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password must be different")
    await db.users.update_one(
        {"id": user.user_id},
        {"$set": {
            "password_hash": hash_password(body.new_password),
            # Lock the seed from resetting this password on future restarts.
            "password_manually_set": True,
            "password_updated_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
        }},
    )
    return {"ok": True, "message": "Password changed successfully"}
