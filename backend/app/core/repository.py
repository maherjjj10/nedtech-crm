"""Generic tenant-scoped repository.

All CRUD operations are tenant-isolated by default.

Security guarantees:
- tenant_id is always controlled by the repository.
- tenant_id cannot be overridden through filters or patches.
- id cannot be changed through updates.
- created_at cannot be changed through updates.
- updated_at is always controlled by the repository.
- aggregate() automatically injects a tenant filter unless explicitly
  configured otherwise.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


# ============================================================
# Utility helpers
# ============================================================

def new_id() -> str:
    return str(uuid.uuid4())


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Fields that are owned by the repository and must never be
# controlled by caller-provided filters or update patches.
PROTECTED_FIELDS = {
    "id",
    "tenant_id",
    "created_at",
    "updated_at",
}


# ============================================================
# Base Repository
# ============================================================

class BaseRepository(Generic[T]):
    """Generic CRUD repository with strict tenant isolation."""

    collection_name: str
    model: type[T]

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        model: type[T],
        collection: str,
    ):
        self.db = db
        self.model = model
        self.collection_name = collection

    @property
    def coll(self):
        return self.db[self.collection_name]

    # ========================================================
    # Internal helpers
    # ========================================================

    @staticmethod
    def _safe_filters(filters: dict | None) -> dict[str, Any]:
        """Remove fields that must never be caller-controlled."""

        if not filters:
            return {}

        return {
            key: value
            for key, value in filters.items()
            if key not in PROTECTED_FIELDS
        }

    @staticmethod
    def _safe_patch(patch: dict) -> dict[str, Any]:
        """Remove repository-owned fields from update payloads."""

        return {
            key: value
            for key, value in patch.items()
            if key not in PROTECTED_FIELDS
            and value is not None
        }

    # ========================================================
    # CREATE
    # ========================================================

    async def create(
        self,
        tenant_id: str,
        data: dict,
    ) -> dict:

        now = utcnow_iso()

        doc = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }

        # Only copy application fields.
        # Repository-owned fields are ignored.
        for key, value in data.items():
            if key not in PROTECTED_FIELDS:
                doc[key] = value

        await self.coll.insert_one(
            {
                **doc,
                "_id": doc["id"],
            }
        )

        return doc

    # ========================================================
    # GET
    # ========================================================

    async def get(
        self,
        tenant_id: str,
        item_id: str,
    ) -> dict | None:

        return await self.coll.find_one(
            {
                "tenant_id": tenant_id,
                "id": item_id,
            },
            {
                "_id": 0,
            },
        )

    # ========================================================
    # LIST
    # ========================================================

    async def list(
        self,
        tenant_id: str,
        filters: dict | None = None,
        sort: list | None = None,
        limit: int = 200,
        skip: int = 0,
    ) -> list[dict]:

        safe_filters = self._safe_filters(filters)

        # IMPORTANT:
        # tenant_id is added AFTER user filters and therefore
        # cannot be overridden by a caller.
        query: dict[str, Any] = {
            **safe_filters,
            "tenant_id": tenant_id,
        }

        cursor = self.coll.find(
            query,
            {
                "_id": 0,
            },
        )

        if sort:
            cursor = cursor.sort(sort)
        else:
            cursor = cursor.sort(
                [
                    ("created_at", -1),
                ]
            )

        cursor = (
            cursor
            .skip(max(skip, 0))
            .limit(max(limit, 0))
        )

        return await cursor.to_list(
            length=max(limit, 0)
        )

    # ========================================================
    # UPDATE
    # ========================================================

    async def update(
        self,
        tenant_id: str,
        item_id: str,
        patch: dict,
    ) -> dict | None:

        safe_patch = self._safe_patch(patch)

        # Repository always controls updated_at.
        safe_patch["updated_at"] = utcnow_iso()

        result = await self.coll.update_one(
            {
                "tenant_id": tenant_id,
                "id": item_id,
            },
            {
                "$set": safe_patch,
            },
        )

        if result.matched_count == 0:
            return None

        return await self.get(
            tenant_id,
            item_id,
        )

    # ========================================================
    # DELETE
    # ========================================================

    async def delete(
        self,
        tenant_id: str,
        item_id: str,
    ) -> bool:

        result = await self.coll.delete_one(
            {
                "tenant_id": tenant_id,
                "id": item_id,
            }
        )

        return result.deleted_count > 0

    # ========================================================
    # COUNT
    # ========================================================

    async def count(
        self,
        tenant_id: str,
        filters: dict | None = None,
    ) -> int:

        safe_filters = self._safe_filters(filters)

        query: dict[str, Any] = {
            **safe_filters,
            "tenant_id": tenant_id,
        }

        return await self.coll.count_documents(query)

    # ========================================================
    # AGGREGATE
    # ========================================================

    async def aggregate(
        self,
        tenant_id: str,
        pipeline: list[dict],
    ) -> list[dict]:
        """Run an aggregation restricted to one tenant.

        The tenant filter is injected automatically.

        If the caller already has a $match stage, the tenant
        condition is merged into it.

        This prevents accidental cross-tenant aggregation.
        """

        if not isinstance(pipeline, list):
            raise TypeError(
                "pipeline must be a list"
            )

        pipeline = [
            dict(stage)
            for stage in pipeline
        ]

        tenant_match = {
            "tenant_id": tenant_id,
        }

        if pipeline and "$match" in pipeline[0]:
            first_match = dict(
                pipeline[0]["$match"]
            )

            # Prevent caller from overriding tenant_id.
            first_match.pop(
                "tenant_id",
                None,
            )

            pipeline[0] = {
                "$match": {
                    **first_match,
                    **tenant_match,
                }
            }

        else:
            pipeline.insert(
                0,
                {
                    "$match": tenant_match,
                },
            )

        return await self.coll.aggregate(
            pipeline
        ).to_list(
            length=None
        )