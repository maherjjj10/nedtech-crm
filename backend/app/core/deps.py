"""FastAPI dependency injection: DB, current user, tenant scope, RBAC."""
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.roles import RANK, PLATFORM_ROLES, normalize_tenant_role, effective_rank
from app.core.security import decode_token


class CurrentUser:
    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,                            # legacy tenant role
        platform_role: Optional[str] = None,  # None | super_admin | platform_owner
        impersonating_from: Optional[str] = None,  # user_id of the platform admin who started impersonation
        original_tenant_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.role = normalize_tenant_role(role) or "viewer"
        self.platform_role = platform_role
        self.impersonating_from = impersonating_from
        self.original_tenant_id = original_tenant_id

    @property
    def is_platform_owner(self) -> bool:
        return self.platform_role == "platform_owner"

    @property
    def is_platform_admin(self) -> bool:
        return self.platform_role in PLATFORM_ROLES

    @property
    def is_impersonating(self) -> bool:
        return self.impersonating_from is not None

    @property
    def effective_rank(self) -> int:
        return effective_rank(self.platform_role, self.role)


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
        role=claims.get("role", "viewer"),
        platform_role=claims.get("platform_role"),
        impersonating_from=claims.get("impersonating_from"),
        original_tenant_id=claims.get("original_tenant_id"),
    )


UserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_tenant_role(*roles: str):
    """Require a minimum tenant role (any of the given roles). Platform admins bypass."""
    allowed = set(roles)

    async def _check(user: UserDep) -> CurrentUser:
        if user.is_platform_admin:
            return user
        if user.role in allowed or user.role == "admin":  # admin implicit
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    return _check


def require_platform_role(min_role: str = "super_admin"):
    """Require a platform_role (defaults to super_admin). Only platform_owner clears platform_owner-min."""
    min_rank = RANK.get(min_role, 90)

    async def _check(user: UserDep) -> CurrentUser:
        if not user.is_platform_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform admin only")
        if RANK.get(user.platform_role, 0) < min_rank:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Higher platform role required")
        return user

    return _check


# Legacy alias — kept because existing routes use `require_role`
def require_role(*roles: str):
    return require_tenant_role(*roles)
