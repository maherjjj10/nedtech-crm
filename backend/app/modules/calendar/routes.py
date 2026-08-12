"""Google Calendar Sync — dormant module.

Endpoints stay wired at all times, but they short-circuit with 503 when
GOOGLE_CLIENT_ID/SECRET are not configured. Once the user pastes the keys and
restarts the backend, calendar sync activates without any code changes.
"""

from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import utcnow_iso


router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"],
    dependencies=[
        Depends(module_gate("calendar")),
        Depends(require_permission("calendar")),
    ],
)


SCOPES = (
    "openid email profile "
    "https://www.googleapis.com/auth/calendar.events"
)

AUTH_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

TOKEN_URL = (
    "https://oauth2.googleapis.com/token"
)

CAL_INSERT = (
    "https://www.googleapis.com/calendar/v3/"
    "calendars/primary/events"
)


def _configured() -> bool:
    return bool(
        settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
    )


@router.get("/status")
async def calendar_status(
    user: UserDep,
):
    doc = await get_db().integrations.find_one(
        {
            "tenant_id": user.tenant_id,
            "provider": "google_calendar",
            "user_id": user.user_id,
        },
        {
            "_id": 0,
            "access_token": 0,
            "refresh_token": 0,
        },
    )

    return {
        "configured": _configured(),
        "connected": bool(doc),
        "connected_at": (
            doc.get("connected_at")
            if doc
            else None
        ),
    }


@router.get("/connect")
async def connect(
    user: UserDep,
    request: Request,
):
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth not configured. "
                "Set GOOGLE_CLIENT_ID/SECRET "
                "in the backend .env"
            ),
        )

    redirect = (
        settings.GOOGLE_REDIRECT_URI
        or (
            f"{settings.FRONTEND_URL}"
            "/api/v1/calendar/callback"
        )
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": user.user_id,
    }

    url = (
        AUTH_URL
        + "?"
        + urlencode(params)
    )

    return {
        "authorize_url": url
    }


@router.get("/callback")
async def callback(
    code: str,
    state: str,
):
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured",
        )

    redirect = (
        settings.GOOGLE_REDIRECT_URI
        or (
            f"{settings.FRONTEND_URL}"
            "/api/v1/calendar/callback"
        )
    )

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": (
                    settings.GOOGLE_CLIENT_ID
                ),
                "client_secret": (
                    settings.GOOGLE_CLIENT_SECRET
                ),
                "redirect_uri": redirect,
                "grant_type": (
                    "authorization_code"
                ),
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=(
                "Failed to exchange "
                "Google auth code"
            ),
        )

    data = response.json()

    user = await get_db().users.find_one(
        {
            "id": state
        },
        {
            "_id": 0
        },
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(
            seconds=data.get(
                "expires_in",
                3600,
            )
        )
    ).isoformat()

    await get_db().integrations.update_one(
        {
            "tenant_id": user["tenant_id"],
            "provider": "google_calendar",
            "user_id": state,
        },
        {
            "$set": {
                "tenant_id": user["tenant_id"],
                "user_id": state,
                "provider": "google_calendar",
                "access_token": data.get(
                    "access_token"
                ),
                "refresh_token": data.get(
                    "refresh_token"
                ),
                "expires_at": expires_at,
                "scope": data.get("scope"),
                "connected_at": utcnow_iso(),
            }
        },
        upsert=True,
    )

    return RedirectResponse(
        f"{settings.FRONTEND_URL}"
        "/settings?calendar=connected"
    )


class SyncTaskIn(BaseModel):
    task_id: str


@router.post("/sync-task")
async def sync_task(
    body: SyncTaskIn,
    user: UserDep,
):
    if not _configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured",
        )

    db = get_db()

    integration = await db.integrations.find_one(
        {
            "tenant_id": user.tenant_id,
            "provider": "google_calendar",
            "user_id": user.user_id,
        }
    )

    if not integration:
        raise HTTPException(
            status_code=400,
            detail=(
                "Connect Google Calendar first"
            ),
        )

    task = await db.tasks.find_one(
        {
            "tenant_id": user.tenant_id,
            "id": body.task_id,
        },
        {
            "_id": 0
        },
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    if not task.get("due_date"):
        raise HTTPException(
            status_code=400,
            detail="Task has no due date",
        )

    event = {
        "summary": task["title"],
        "description": (
            task.get("description")
            or ""
        ),
        "start": {
            "date": task["due_date"]
        },
        "end": {
            "date": task["due_date"]
        },
    }

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.post(
            CAL_INSERT,
            headers={
                "Authorization": (
                    f"Bearer "
                    f"{integration['access_token']}"
                )
            },
            json=event,
        )

    if response.status_code >= 300:
        raise HTTPException(
            status_code=502,
            detail=(
                "Google Calendar error: "
                f"{response.text}"
            ),
        )

    google_event = response.json()

    await db.tasks.update_one(
        {
            "tenant_id": user.tenant_id,
            "id": body.task_id,
        },
        {
            "$set": {
                "google_event_id": (
                    google_event.get("id")
                ),
                "updated_at": utcnow_iso(),
            }
        },
    )

    return {
        "synced": True,
        "event_id": google_event.get("id"),
        "html_link": google_event.get(
            "htmlLink"
        ),
    }