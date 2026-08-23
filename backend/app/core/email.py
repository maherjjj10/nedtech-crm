"""NED Tech CRM email helper using Resend."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_html_email(
    *,
    to: str,
    subject: str,
    html: str,
    reply_to: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict:
    """
    Send an HTML email through Resend.

    Supports:
    - HTML emails
    - reply-to
    - optional PDF/file attachments
    - backward compatibility with existing callers

    attachments format:

    [
        {
            "filename": "QUO-00001.pdf",
            "content": "<base64 encoded content>",
            "content_type": "application/pdf",
        }
    ]
    """

    api_key = os.environ.get(
        "RESEND_API_KEY",
        "",
    ).strip()

    from_name = os.environ.get(
        "EMAIL_FROM_NAME",
        "NED Tech CRM",
    ).strip()

    from_address = os.environ.get(
        "EMAIL_FROM_ADDRESS",
        "info@tapbyned.com",
    ).strip()

    if not api_key:
        logger.error(
            "RESEND_API_KEY is not configured."
        )

        return {
            "sent": False,
            "reason": "email_not_configured",
        }

    if not to:
        logger.error(
            "Cannot send email without recipient."
        )

        return {
            "sent": False,
            "reason": "recipient_missing",
        }

    # ---------------------------------------------------------
    # Sender
    # ---------------------------------------------------------

    sender = f"{from_name} <{from_address}>"

    # ---------------------------------------------------------
    # Resend payload
    # ---------------------------------------------------------

    payload: dict[str, Any] = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    if reply_to:
        payload["reply_to"] = reply_to

    # ---------------------------------------------------------
    # Attachments
    # ---------------------------------------------------------

    if attachments:
        resend_attachments = []

        for attachment in attachments:
            filename = attachment.get("filename")
            content = attachment.get("content")

            if not filename or not content:
                logger.warning(
                    "Skipping invalid email attachment."
                )
                continue

            # Resend accepts base64 content.
            if isinstance(content, bytes):
                content = base64.b64encode(
                    content
                ).decode("ascii")

            resend_attachments.append(
                {
                    "filename": filename,
                    "content": content,
                }
            )

        if resend_attachments:
            payload["attachments"] = resend_attachments

    # ---------------------------------------------------------
    # Send
    # ---------------------------------------------------------

    try:
        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        # -----------------------------------------------------
        # Resend error
        # -----------------------------------------------------

        if response.status_code >= 300:
            logger.error(
                "Resend email failed: %s %s",
                response.status_code,
                response.text,
            )

            try:
                error_data = response.json()
            except Exception:
                error_data = {}

            return {
                "sent": False,
                "reason": "provider_error",
                "status_code": response.status_code,
                "error": error_data,
            }

        # -----------------------------------------------------
        # Success
        # -----------------------------------------------------

        try:
            response_data = response.json()
        except Exception:
            response_data = {}

        email_id = response_data.get("id")

        logger.info(
            "Email sent successfully via Resend: "
            "recipient=%s id=%s",
            to,
            email_id,
        )

        return {
            "sent": True,
            "id": email_id,
        }

    except httpx.TimeoutException:
        logger.exception(
            "Resend email request timed out."
        )

        return {
            "sent": False,
            "reason": "timeout",
        }

    except httpx.HTTPError:
        logger.exception(
            "Resend HTTP error."
        )

        return {
            "sent": False,
            "reason": "http_error",
        }

    except Exception:
        logger.exception(
            "Unexpected Resend email exception."
        )

        return {
            "sent": False,
            "reason": "exception",
        }