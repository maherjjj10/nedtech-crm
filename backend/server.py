"""NED Tech CRM/ERP — FastAPI application entrypoint.

Clean layered architecture:
  - app.core.*   : configuration, database, security, deps, module registry
  - app.modules.*: feature modules (each self-contained: routes + models)

Every module registers a router; module_gate() enforces per-tenant toggles.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import logging

from app.core.config import settings
from app.core.database import close_db, ensure_indexes
from app.core.module_registry import list_modules
from app.core.seed import seed_platform_owner

from app.modules.registry import (
    SYSTEM_ROUTERS,
    MODULES,
    PUBLIC_ROUTERS,
)

from app.modules.billing.webhook import (
    webhook_router as stripe_webhook_router
)

from app.modules.platform.routes import (
    router as platform_router
)

# Suppliers
from app.modules.suppliers.routes import (
    router as suppliers_router
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("nedtech")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_platform_owner()

    logger.info("NED Tech CRM ready.")

    yield

    await close_db()


app = FastAPI(
    title="NED Tech CRM/ERP",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ============================================================
# MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,
    same_site="lax",
)


# ============================================================
# API v1
# ============================================================

api_v1 = APIRouter(
    prefix="/api/v1"
)


# ============================================================
# SYSTEM ROUTERS
# ============================================================

for router in SYSTEM_ROUTERS:
    api_v1.include_router(router)


# ============================================================
# TOGGLEABLE MODULE ROUTERS
# ============================================================

for module in list_modules():
    api_v1.include_router(module.router)


# ============================================================
# SUPPLIERS
# ============================================================
#
# Suppliers are mounted directly under:
#
# /api/v1/suppliers
#
# NOT:
#
# /api/v1/clients/suppliers
#
# ============================================================

api_v1.include_router(
    suppliers_router
)


# ============================================================
# CLIENT 360 SUBRESOURCES
# ============================================================

from app.modules.client_notes.routes import (
    router as _client_notes_router
)

api_v1.include_router(
    _client_notes_router
)


# ============================================================
# FINANCE SUBRESOURCES
# ============================================================

from app.modules.registry import (
    quote_flow_router as _qf_router,
    contracts_router as _ct_router,
)

api_v1.include_router(
    _qf_router
)

api_v1.include_router(
    _ct_router
)


# ============================================================
# PLATFORM ADMIN
# ============================================================

api_v1.include_router(
    platform_router
)


# ============================================================
# PUBLIC ROUTERS
# ============================================================
#
# Unauthenticated share-token routes for quotes/contracts.
# ============================================================

for router in PUBLIC_ROUTERS:
    api_v1.include_router(router)


# ============================================================
# HEALTH
# ============================================================

@api_v1.get(
    "/health",
    tags=["System"]
)
async def health():
    return {
        "status": "ok",
        "app": "NED Tech CRM",
        "version": "1.0.0",
    }


# ============================================================
# MODULE CATALOG
# ============================================================

@api_v1.get(
    "/modules",
    tags=["System"]
)
async def modules_catalog():
    return [
        {
            "code": module.code,
            "name": module.name,
            "default_enabled": module.default_enabled,
        }
        for module in list_modules()
    ]


# ============================================================
# MOUNT API
# ============================================================

app.include_router(
    api_v1
)


# ============================================================
# STRIPE WEBHOOK
# ============================================================
#
# Must remain exactly:
#
# /api/stripe/webhook
#
# ============================================================

app.include_router(
    stripe_webhook_router
)


# ============================================================
# LEGACY /api PING
# ============================================================

@app.get(
    "/api/"
)
async def root():
    return {
        "app": "NED Tech CRM",
        "api": "/api/v1",
    }