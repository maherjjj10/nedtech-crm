"""Role hierarchy and module permissions."""

from typing import Optional


# ============================================================
# ROLE HIERARCHY
# ============================================================

PLATFORM_ROLES = (
    "platform_owner",
    "super_admin",
)

TENANT_ROLES = (
    "admin",
    "manager",
    "employee",
    "viewer",
)


# Legacy roles from older versions of the application.
LEGACY_TENANT_ALIASES = {
    "owner": "admin",
    "member": "employee",
}


# Higher number = higher authority.
RANK = {
    "platform_owner": 100,
    "super_admin": 90,
    "admin": 60,
    "manager": 40,
    "employee": 20,
    "viewer": 10,
}


def normalize_tenant_role(
    role: Optional[str],
) -> Optional[str]:
    """
    Convert legacy tenant roles to the current role system.

    owner  -> admin
    member -> employee
    """

    if role is None:
        return None

    return LEGACY_TENANT_ALIASES.get(role, role)


def effective_rank(
    platform_role: Optional[str],
    tenant_role: Optional[str],
) -> int:
    """
    Return the highest rank available to the user.
    """

    return max(
        RANK.get(platform_role or "", 0),
        RANK.get(
            normalize_tenant_role(tenant_role) or "",
            0,
        ),
    )


def is_platform_admin(
    platform_role: Optional[str],
) -> bool:
    return platform_role in PLATFORM_ROLES


def is_platform_owner(
    platform_role: Optional[str],
) -> bool:
    return platform_role == "platform_owner"


def can_grant(
    actor_platform: Optional[str],
    actor_tenant: Optional[str],
    target_platform: Optional[str],
    target_tenant: Optional[str],
) -> bool:
    """
    A user can only grant a role whose effective rank
    is less than or equal to their own rank.
    """

    return (
        effective_rank(
            actor_platform,
            actor_tenant,
        )
        >=
        effective_rank(
            target_platform,
            target_tenant,
        )
    )


# ============================================================
# MODULE PERMISSIONS
# ============================================================

PERMISSION_MODULES = (
    "dashboard",
    "crm",
    "sales",
    "tasks",
    "finance",
    "products",
    "hr",
    "ai",
    "calendar",
    "contracts",
    "billing",
    "profile",
    "settings",
)


def default_permissions() -> dict[str, bool]:
    """
    Default permissions for a newly created employee.

    Basic CRM/workflow modules are enabled.

    Sensitive modules such as:
        finance
        hr
        billing
        settings

    are disabled by default.
    """

    return {
        "dashboard": True,
        "crm": True,
        "sales": True,
        "tasks": True,
        "finance": False,
        "products": False,
        "hr": False,
        "ai": False,
        "calendar": True,
        "contracts": True,
        "billing": False,
        "profile": True,
        "settings": False,
    }


def normalize_permissions(
    permissions: Optional[dict[str, bool]] = None,
) -> dict[str, bool]:
    """
    Normalize stored permissions.

    Missing permissions automatically receive safe defaults.
    """

    defaults = default_permissions()

    if not permissions:
        return defaults

    normalized = defaults.copy()

    for module in PERMISSION_MODULES:
        if module in permissions:
            normalized[module] = bool(
                permissions[module]
            )

    return normalized


def has_permission(
    *,
    platform_role: Optional[str],
    permissions: Optional[dict[str, bool]],
    module: str,
) -> bool:
    """
    Check whether a user has access to a module.

    Platform owners and super admins have unrestricted access.
    """

    if platform_role in PLATFORM_ROLES:
        return True

    normalized = normalize_permissions(
        permissions
    )

    return bool(
        normalized.get(module, False)
    )