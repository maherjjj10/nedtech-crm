"""Role hierarchy + authorization helpers.

Two role scopes, kept separate per authorization best practices:
  - platform_role: platform_owner > super_admin > (None)
      Applies across every tenant. Only platform users have this.
  - tenant_role: admin > manager > employee > viewer
      Applies within a single tenant. Every workspace member has one.

The 6-tier hierarchy the user asked for is the union of both scopes, ranked:
  platform_owner (rank 100) > super_admin (90) > admin (60) > manager (40)
  > employee (20) > viewer (10)
"""
from typing import Optional

PLATFORM_ROLES = ("platform_owner", "super_admin")
TENANT_ROLES = ("admin", "manager", "employee", "viewer")

# Backwards-compat: legacy tenant role "owner" (from V1 registration) maps to "admin".
LEGACY_TENANT_ALIASES = {"owner": "admin", "member": "employee"}

RANK = {
    "platform_owner": 100,
    "super_admin": 90,
    "admin": 60,
    "manager": 40,
    "employee": 20,
    "viewer": 10,
}


def normalize_tenant_role(role: Optional[str]) -> Optional[str]:
    if role is None:
        return None
    return LEGACY_TENANT_ALIASES.get(role, role)


def effective_rank(platform_role: Optional[str], tenant_role: Optional[str]) -> int:
    """Highest rank among the two scopes."""
    return max(
        RANK.get(platform_role or "", 0),
        RANK.get(normalize_tenant_role(tenant_role) or "", 0),
    )


def is_platform_admin(platform_role: Optional[str]) -> bool:
    return platform_role in PLATFORM_ROLES


def is_platform_owner(platform_role: Optional[str]) -> bool:
    return platform_role == "platform_owner"


def can_grant(actor_platform: Optional[str], actor_tenant: Optional[str],
              target_platform: Optional[str], target_tenant: Optional[str]) -> bool:
    """A principal may only grant a role <= their own effective rank."""
    return effective_rank(actor_platform, actor_tenant) >= effective_rank(target_platform, target_tenant)
