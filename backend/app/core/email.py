"""Emergent-managed Resend email helper.

If EMERGENT_EMAIL_KEY is not yet provisioned the caller can still ship the
feature — it just returns `sent=False` and the app surfaces a "copy invite link"
fallback so no user action is blocked.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"


async def send_html_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> dict:
    key = os.environ.get("EMERGENT_EMAIL_KEY", "")
    from_name = os.environ.get("EMAIL_FROM_NAME", "NED Tech CRM")
    if not key:
        logger.warning("EMERGENT_EMAIL_KEY not set — email send skipped (recipient=%s)", to)
        return {"sent": False, "reason": "email_not_configured"}

    payload = {"to": [to], "subject": subject, "html": html, "from_name": from_name}
    if reply_to:
        payload["contact_email"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": key},
                json=payload,
            )
        if resp.status_code >= 300:
            logger.error("Email send failed: %s %s", resp.status_code, resp.text)
            return {"sent": False, "reason": "provider_error"}
        return {"sent": True, "id": resp.json().get("id")}
    except Exception as e:
        logger.exception("Email send exception: %s", e)
        return {"sent": False, "reason": "exception"}
