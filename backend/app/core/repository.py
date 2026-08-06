"""Generic tenant-scoped repository.

Business logic (services) MUST use these repositories rather than talking to
Mongo directly. This lets us swap the storage engine (e.g. Postgres) later
without touching the service layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseRepository(Generic[T]):
    """CRUD helpers with automatic tenant scoping."""

    collection_name: str
    model: type[T]

    def __init__(self, db: AsyncIOMotorDatabase, model: type[T], collection: str):
        self.db = db
        self.model = model
        self.collection_name = collection

    @property
    def coll(self):
        return self.db[self.collection_name]

    async def create(self, tenant_id: str, data: dict) -> dict:
        doc = {
            "id": data.get("id") or new_id(),
            "tenant_id": tenant_id,
            "created_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
            **{k: v for k, v in data.items() if k not in ("id", "tenant_id", "created_at", "updated_at")},
        }
        await self.coll.insert_one({**doc, "_id": doc["id"]})
        return doc

    async def get(self, tenant_id: str, item_id: str) -> dict | None:
        return await self.coll.find_one(
            {"tenant_id": tenant_id, "id": item_id}, {"_id": 0}
        )

    async def list(
        self,
        tenant_id: str,
        filters: dict | None = None,
        sort: list | None = None,
        limit: int = 200,
        skip: int = 0,
    ) -> list[dict]:
        q: dict[str, Any] = {"tenant_id": tenant_id, **(filters or {})}
        cursor = self.coll.find(q, {"_id": 0})
        if sort:
            cursor = cursor.sort(sort)
        else:
            cursor = cursor.sort([("created_at", -1)])
        cursor = cursor.skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def update(self, tenant_id: str, item_id: str, patch: dict) -> dict | None:
        patch = {k: v for k, v in patch.items() if v is not None}
        patch["updated_at"] = utcnow_iso()
        await self.coll.update_one(
            {"tenant_id": tenant_id, "id": item_id}, {"$set": patch}
        )
        return await self.get(tenant_id, item_id)

    async def delete(self, tenant_id: str, item_id: str) -> bool:
        r = await self.coll.delete_one({"tenant_id": tenant_id, "id": item_id})
        return r.deleted_count > 0

    async def count(self, tenant_id: str, filters: dict | None = None) -> int:
        q: dict[str, Any] = {"tenant_id": tenant_id, **(filters or {})}
        return await self.coll.count_documents(q)

    async def aggregate(self, pipeline: list[dict]) -> list[dict]:
        return await self.coll.aggregate(pipeline).to_list(length=None)
