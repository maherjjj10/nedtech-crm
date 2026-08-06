"""Module registration — the single place that wires all modules into the API."""
from app.core.module_registry import ModuleDefinition, register_module

from app.modules.auth.routes import router as auth_router
from app.modules.tenants.routes import router as tenants_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.clients.routes import router as clients_router
from app.modules.client_notes.routes import router as client_notes_router
from app.modules.pipeline.routes import router as pipeline_router
from app.modules.tasks.routes import router as tasks_router
from app.modules.finance.routes import router as finance_router
from app.modules.products.routes import router as products_router
from app.modules.employees.routes import router as employees_router
from app.modules.ai.routes import router as ai_router
from app.modules.invites.routes import router as invites_router
from app.modules.billing.routes import router as billing_router
from app.modules.calendar.routes import router as calendar_router


# System modules (always enabled — not user-toggleable)
SYSTEM_ROUTERS = [
    auth_router, tenants_router, dashboard_router,
    invites_router, billing_router,
]

# Toggleable modules
MODULES = [
    ModuleDefinition(code="crm", name="CRM", router=clients_router),
    # Client 360 subresources ride under the CRM module gate as well
    ModuleDefinition(code="crm", name="Client 360", router=client_notes_router),
    ModuleDefinition(code="sales", name="Sales Pipeline", router=pipeline_router),
    ModuleDefinition(code="tasks", name="Tasks & Projects", router=tasks_router),
    ModuleDefinition(code="finance", name="Finance", router=finance_router),
    ModuleDefinition(code="products", name="Products & Services", router=products_router),
    ModuleDefinition(code="hr", name="Employees", router=employees_router),
    ModuleDefinition(code="ai", name="AI Assistant", router=ai_router),
    ModuleDefinition(code="calendar", name="Calendar", router=calendar_router),
]

# de-dup by (code + router id) — allow two routers to share the same gate
_seen = set()
for m in MODULES:
    if id(m.router) in _seen:
        continue
    _seen.add(id(m.router))
    register_module(m)
