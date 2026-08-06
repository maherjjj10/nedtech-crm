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
from app.modules.registry import SYSTEM_ROUTERS, MODULES  # noqa: F401  (side-effect: registers modules)
from app.modules.billing.webhook import webhook_router as stripe_webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nedtech")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET, same_site="lax")


# ------- API v1 -------
api_v1 = APIRouter(prefix="/api/v1")

# System routers
for r in SYSTEM_ROUTERS:
    api_v1.include_router(r)

# Toggleable module routers (registered exactly once even when several share a gate)
_seen_ids = set()
for m in list_modules():
    if id(m.router) in _seen_ids:
        continue
    _seen_ids.add(id(m.router))
    api_v1.include_router(m.router)

# Register additional routers that share an existing module gate (Client 360 notes/timeline)
from app.modules.client_notes.routes import router as _client_notes_router  # noqa: E402
if id(_client_notes_router) not in _seen_ids:
    api_v1.include_router(_client_notes_router)


@api_v1.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "app": "NED Tech CRM", "version": "1.0.0"}


@api_v1.get("/modules", tags=["System"])
async def modules_catalog():
    return [
        {"code": m.code, "name": m.name, "default_enabled": m.default_enabled}
        for m in list_modules()
    ]


app.include_router(api_v1)
# Stripe webhook (must be at exactly /api/stripe/webhook)
app.include_router(stripe_webhook_router)


# ------- Legacy /api ping for platform health probes -------
@app.get("/api/")
async def root():
    return {"app": "NED Tech CRM", "api": "/api/v1"}
