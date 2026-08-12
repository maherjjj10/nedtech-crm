"""FastAPI dependency injection: DB, current user, tenant scope, RBAC."""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.roles import (
    RANK,
    PLATFORM_ROLES,
    normalize_tenant_role,
    effective_rank,
    normalize_permissions,
    has_permission,
)
from app.core.security import decode_token


def _extract_token(
    request: Request | None,
    authorization: str | None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Missing bearer token",
    )


def decode_current_token(request: Request) -> tuple[str, dict]:
    """Utility used by session-management routes to read the current jti."""

    auth = (
        request.headers.get("authorization")
        or request.headers.get("Authorization")
        or ""
    )

    token = _extract_token(request, auth)

    try:
        claims = decode_token(token)
    except Exception:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )

    return token, claims


class CurrentUser:
    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
        platform_role: Optional[str] = None,
        impersonating_from: Optional[str] = None,
        original_tenant_id: Optional[str] = None,
        permissions: Optional[dict[str, bool]] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email

        # Normalize legacy tenant roles:
        # owner  -> admin
        # member -> employee
        self.role = normalize_tenant_role(role) or "viewer"

        self.platform_role = platform_role
        self.impersonating_from = impersonating_from
        self.original_tenant_id = original_tenant_id

        # Employee/module permissions.
        # Missing permissions receive safe defaults.
        self.permissions = normalize_permissions(permissions)

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
        return effective_rank(
            self.platform_role,
            self.role,
        )

    def can(self, module: str) -> bool:
        """
        Check whether the current user has access to a module.

        Platform owners and super admins automatically have full access.
        """
        return has_permission(
            platform_role=self.platform_role,
            permissions=self.permissions,
            module=module,
        )


def db_dep() -> AsyncIOMotorDatabase:
    return get_db()


DBDep = Annotated[
    AsyncIOMotorDatabase,
    Depends(db_dep),
]


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """
    Resolve the currently authenticated user.

    Authentication and tenant/platform context come from the JWT.

    Permissions are loaded from MongoDB so that changing an employee's
    permissions takes effect without requiring a new JWT.
    """

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = decode_token(token)
    except Exception:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )

    # Session revocation check.
    # Only tokens containing a jti participate in session tracking.
    jti = claims.get("jti")

    if jti:
        session = await get_db().sessions.find_one(
            {"id": jti}
        )

        if session and session.get("revoked_at"):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "This session has been signed out",
            )

    # ------------------------------------------------------------
    # Load the current user from MongoDB.
    # ------------------------------------------------------------
    #
    # This is important because permissions are intentionally NOT
    # stored only inside the JWT.
    #
    # If an admin changes:
    #
    #     finance: false -> true
    #
    # the change becomes effective on the next API request.
    #
    user_doc = await get_db().users.find_one(
        {
            "id": claims["sub"],
            "tenant_id": claims["tenant_id"],
        },
        {
            "_id": 0,
            "id": 1,
            "email": 1,
            "role": 1,
            "permissions": 1,
        },
    )

    if not user_doc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "User account not found",
        )

    return CurrentUser(
        user_id=user_doc["id"],
        tenant_id=claims["tenant_id"],
        email=user_doc.get(
            "email",
            claims.get("email", ""),
        ),
        role=user_doc.get(
            "role",
            claims.get("role", "viewer"),
        ),
        platform_role=claims.get("platform_role"),
        impersonating_from=claims.get("impersonating_from"),
        original_tenant_id=claims.get("original_tenant_id"),
        permissions=user_doc.get("permissions"),
    )


UserDep = Annotated[
    CurrentUser,
    Depends(get_current_user),
]


def require_tenant_role(*roles: str):
    """
    Require a minimum tenant role.

    Platform admins bypass tenant-role restrictions.
    """

    allowed = set(
        normalize_tenant_role(role) or role
        for role in roles
    )

    async def _check(user: UserDep) -> CurrentUser:
        if user.is_platform_admin:
            return user

        if user.role in allowed or user.role == "admin":
            return user

        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Insufficient permissions",
        )

    return _check


def require_platform_role(
    min_role: str = "super_admin",
):
    """
    Require a minimum platform role.

    Only platform admins can pass this check.
    """

    min_rank = RANK.get(
        min_role,
        90,
    )

    async def _check(user: UserDep) -> CurrentUser:
        if not user.is_platform_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Platform admin only",
            )

        if RANK.get(
            user.platform_role,
            0,
        ) < min_rank:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Higher platform role required",
            )

        return user

    return _check


def require_permission(module: str):
    """
    Require access to a specific CRM module.

    Example:

        @router.get(
            "",
            dependencies=[Depends(require_permission("finance"))],
        )

    Platform owners and super admins automatically pass.
    """

    async def _check(user: UserDep) -> CurrentUser:
        if user.can(module):
            return user

        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Permission denied for module '{module}'.",
        )

    return _check


# Legacy alias — kept because existing routes use require_role.
def require_role(*roles: str):
    return require_tenant_role(*roles)