"""Modular activation registry.

Every module registers itself here.

Each request to a module is checked against two separate layers:

1. Workspace module activation
   - Is the module enabled for this tenant?

2. User module permission
   - Does the current user have permission to access this module?

Platform owners and super admins have unrestricted access.
Tenant admins also have full module access.
Managers, employees and viewers use their stored permissions.
"""

from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter, HTTPException, status

from app.core.deps import UserDep


# ============================================================
# MODULE DEFINITION
# ============================================================

@dataclass
class ModuleDefinition:
    code: str
    name: str
    router: APIRouter
    default_enabled: bool = True
    depends_on: list[str] = field(default_factory=list)


# ============================================================
# REGISTRY
# ============================================================

_registry: dict[str, ModuleDefinition] = {}


def register_module(mod: ModuleDefinition) -> None:
    """Register a module in the central registry."""

    _registry[mod.code] = mod


def list_modules() -> list[ModuleDefinition]:
    """Return all registered modules."""

    return list(_registry.values())


def get_module(
    code: str,
) -> ModuleDefinition | None:
    """Return a module definition by code."""

    return _registry.get(code)


# ============================================================
# MODULE ACCESS GATE
# ============================================================

def module_gate(code: str) -> Callable:
    """
    Protect a module at the API/router level.

    Access requires:

    1. The tenant/workspace exists.
    2. The module is enabled for the tenant.
    3. The current user has permission for that module.

    Platform owners and super admins automatically pass.

    Tenant admins also automatically pass because they are
    workspace administrators.

    Managers, employees and viewers are checked against their
    individual module permissions.
    """

    from app.core.database import get_db

    async def _gate(user: UserDep):
        # ----------------------------------------------------
        # 1. Find tenant
        # ----------------------------------------------------

        tenant = await get_db().tenants.find_one(
            {
                "id": user.tenant_id,
            },
            {
                "_id": 0,
            },
        )

        if not tenant:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Tenant not found",
            )

        # ----------------------------------------------------
        # 2. Check workspace module activation
        # ----------------------------------------------------

        modules = tenant.get(
            "modules",
            {},
        )

        if not modules.get(
            code,
            True,
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Module '{code}' is disabled for this workspace.",
            )

        # ----------------------------------------------------
        # 3. Platform admins bypass permissions
        # ----------------------------------------------------

        if user.is_platform_admin:
            return user

        # ----------------------------------------------------
        # 4. Tenant admins bypass employee permissions
        # ----------------------------------------------------
        #
        # Legacy "owner" is normalized to "admin".
        #
        # This prevents existing workspace owners/admins from
        # accidentally losing access because their old user
        # document does not contain a permissions object.
        # ----------------------------------------------------

        if user.role == "admin":
            return user

        # ----------------------------------------------------
        # 5. Check individual employee permission
        # ----------------------------------------------------

        if not user.can(code):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Permission denied for module '{code}'.",
            )

        return user

    return _gate