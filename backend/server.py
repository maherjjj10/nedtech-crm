"""NED Tech CRM/ERP — FastAPI application entrypoint."""

import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import (
    close_db,
    ensure_indexes,
)
from app.core.module_registry import list_modules
from app.core.seed import seed_platform_owner

from app.core.invoice_scheduler import (
    invoice_scheduler,
)

from app.modules.registry import (
    SYSTEM_ROUTERS,
    PUBLIC_ROUTERS,
)

from app.modules.billing.webhook import (
    webhook_router as stripe_webhook_router,
)

from app.modules.platform.routes import (
    router as platform_router,
)

from app.modules.suppliers.routes import (
    router as suppliers_router,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "nedtech"
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # --------------------------------------------------------
    # Database initialization
    # --------------------------------------------------------

    await ensure_indexes()

    # --------------------------------------------------------
    # Platform initialization
    # --------------------------------------------------------

    await seed_platform_owner()

    # --------------------------------------------------------
    # Invoice scheduler
    # --------------------------------------------------------

    scheduler_task = asyncio.create_task(
        invoice_scheduler()
    )

    logger.info(
        "NED Tech CRM ready."
    )

    logger.info(
        "Invoice scheduler started."
    )

    try:
        yield

    finally:

        # ----------------------------------------------------
        # Stop scheduler cleanly
        # ----------------------------------------------------

        scheduler_task.cancel()

        try:
            await scheduler_task

        except asyncio.CancelledError:
            pass

        logger.info(
            "Invoice scheduler stopped."
        )

        # ----------------------------------------------------
        # Close database
        # ----------------------------------------------------

        await close_db()

        logger.info(
            "NED Tech CRM shutdown complete."
        )


# ============================================================
# FASTAPI APPLICATION
# ============================================================

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
# API V1
# ============================================================

api_v1 = APIRouter(
    prefix="/api/v1",
)


# ============================================================
# SYSTEM ROUTERS
# ============================================================

for router in SYSTEM_ROUTERS:
    api_v1.include_router(
        router
    )


# ============================================================
# TOGGLEABLE MODULE ROUTERS
# ============================================================

for module in list_modules():
    api_v1.include_router(
        module.router
    )


# ============================================================
# SUPPLIERS
# ============================================================

api_v1.include_router(
    suppliers_router
)


# ============================================================
# CLIENT 360
# ============================================================

from app.modules.client_notes.routes import (
    router as _client_notes_router,
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

for router in PUBLIC_ROUTERS:
    api_v1.include_router(
        router
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@api_v1.get(
    "/health",
    tags=["System"],
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
    tags=["System"],
)
async def modules_catalog():

    return [
        {
            "code": module.code,
            "name": module.name,
            "default_enabled": (
                module.default_enabled
            ),
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

app.include_router(
    stripe_webhook_router
)


# ============================================================
# LEGACY /api PING
# ============================================================

@app.get(
    "/api/",
)
async def root():

    return {
        "app": "NED Tech CRM",
        "api": "/api/v1",
    }