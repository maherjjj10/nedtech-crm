"""Notifications module."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.repository import new_id, utcnow_iso


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[
        Depends(require_permission("dashboard")),
    ],
)


class NotificationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    message: Optional[str] = None

    type: str = "info"

    entity_type: Optional[str] = None

    entity_id: Optional[str] = None

    url: Optional[str] = None


def _build_notification(
    user,
    body: NotificationCreate,
):
    notification_id = new_id()

    return {
        "_id": notification_id,
        "id": notification_id,
        "tenant_id": user.tenant_id,
        "user_id": user.email,
        "title": body.title,
        "message": body.message,
        "type": body.type,
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "url": body.url,
        "read": False,
        "created_at": utcnow_iso(),
    }


@router.get("")
async def list_notifications(
    user: UserDep,
    unread_only: bool = Query(
        default=False
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
):
    db = get_db()

    filters = {
        "tenant_id": user.tenant_id,
        "user_id": user.email,
    }

    if unread_only:
        filters["read"] = False

    cursor = (
        db.notifications
        .find(
            filters,
            {
                "_id": 0,
            },
        )
        .sort(
            "created_at",
            -1,
        )
        .limit(limit)
    )

    notifications = await cursor.to_list(
        length=limit
    )

    unread_count = await db.notifications.count_documents(
        {
            "tenant_id": user.tenant_id,
            "user_id": user.email,
            "read": False,
        }
    )

    return {
        "items": notifications,
        "unread_count": unread_count,
    }


@router.post(
    "",
    status_code=201,
)
async def create_notification(
    body: NotificationCreate,
    user: UserDep,
):
    db = get_db()

    notification = _build_notification(
        user,
        body,
    )

    await db.notifications.insert_one(
        notification
    )

    notification.pop(
        "_id",
        None,
    )

    return notification


@router.patch(
    "/{notification_id}/read"
)
async def mark_notification_read(
    notification_id: str,
    user: UserDep,
):
    db = get_db()

    result = await db.notifications.update_one(
        {
            "id": notification_id,
            "tenant_id": user.tenant_id,
            "user_id": user.email,
        },
        {
            "$set": {
                "read": True,
                "read_at": utcnow_iso(),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return {
        "ok": True,
        "id": notification_id,
    }


@router.patch(
    "/read-all"
)
async def mark_all_notifications_read(
    user: UserDep,
):
    db = get_db()

    result = await db.notifications.update_many(
        {
            "tenant_id": user.tenant_id,
            "user_id": user.email,
            "read": False,
        },
        {
            "$set": {
                "read": True,
                "read_at": utcnow_iso(),
            }
        },
    )

    return {
        "ok": True,
        "updated": result.modified_count,
    }


@router.delete(
    "/{notification_id}",
    status_code=204,
)
async def delete_notification(
    notification_id: str,
    user: UserDep,
):
    db = get_db()

    result = await db.notifications.delete_one(
        {
            "id": notification_id,
            "tenant_id": user.tenant_id,
            "user_id": user.email,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return None
