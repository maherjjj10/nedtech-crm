"""MongoDB connection and index bootstrap.

The rest of the application talks to Mongo through Repository classes only,
never directly. This keeps the persistence layer swappable.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL, uuidRepresentation="standard")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[settings.DB_NAME]
    return _db


async def ensure_indexes() -> None:
    """Ensure indexes exist for tenant isolation and hot paths."""
    db = get_db()

    # Users
    await db.users.create_index("email", unique=True)
    # partial index: only enforce uniqueness when google_sub is an actual string
    # (a plain sparse index still indexes documents with google_sub=null, which breaks
    #  registration for password-only users).
    try:
        await db.users.drop_index("google_sub_1")
    except Exception:
        pass
    await db.users.create_index(
        [("google_sub", 1)],
        unique=True,
        partialFilterExpression={"google_sub": {"$type": "string"}},
    )
    await db.users.create_index([("tenant_id", 1)])

    # Tenants
    await db.tenants.create_index("slug", unique=True)

    # Every tenant-scoped collection: compound index (tenant_id, created_at)
    tenant_scoped = [
        "clients",
        "deals",
        "tasks",
        "projects",
        "invoices",
        "quotes",
        "expenses",
        "products",
        "employees",
        "activities",
        "ai_conversations",
        "billing",
    ]
    for coll in tenant_scoped:
        await db[coll].create_index([("tenant_id", 1), ("created_at", -1)])
        await db[coll].create_index([("tenant_id", 1), ("id", 1)])

    # Text search on clients and deals
    await db.clients.create_index(
        [("tenant_id", 1), ("name", "text"), ("email", "text"), ("company", "text")]
    )
    logger.info("MongoDB indexes ensured.")


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
