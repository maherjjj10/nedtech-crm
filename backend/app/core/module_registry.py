"""Modular activation registry.

Every module registers itself here. Tenants can enable/disable individual
modules; requests to disabled modules are blocked at the router level.
"""
from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter, HTTPException, status

from app.core.deps import UserDep


@dataclass
class ModuleDefinition:
    code: str            # short id: "crm", "finance", "hr", "ai" ...
    name: str            # human-readable label
    router: APIRouter
    default_enabled: bool = True
    depends_on: list[str] = field(default_factory=list)


_registry: dict[str, ModuleDefinition] = {}


def register_module(mod: ModuleDefinition) -> None:
    _registry[mod.code] = mod


def list_modules() -> list[ModuleDefinition]:
    return list(_registry.values())


def get_module(code: str) -> ModuleDefinition | None:
    return _registry.get(code)


def module_gate(code: str) -> Callable:
    """Dependency that blocks the request if the tenant disabled the module."""
    from app.core.database import get_db

    async def _gate(user: UserDep):
        tenant = await get_db().tenants.find_one({"id": user.tenant_id}, {"_id": 0})
        if not tenant:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
        modules = tenant.get("modules", {})
        if not modules.get(code, True):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Module '{code}' is disabled for this workspace.",
            )
        return user

    return _gate
