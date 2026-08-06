"""FastAPI dependency injection: DB, current user, tenant scope, RBAC."""
from typing import Annotated
from fastapi import Depends, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import decode_token


class CurrentUser:
    def __init__(self, user_id: str, tenant_id: str, email: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.role = role


def db_dep() -> AsyncIOMotorDatabase:
    return get_db()


DBDep = Annotated[AsyncIOMotorDatabase, Depends(db_dep)]


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = decode_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return CurrentUser(
        user_id=claims["sub"],
        tenant_id=claims["tenant_id"],
        email=claims.get("email", ""),
        role=claims.get("role", "member"),
    )


UserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*roles: str):
    async def _check(user: UserDep) -> CurrentUser:
        if user.role not in roles and user.role != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _check
