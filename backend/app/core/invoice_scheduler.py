"""Automatic invoice status and reminder scheduler."""

import asyncio
import logging
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.repository import new_id, utcnow_iso


logger = logging.getLogger("nedtech.invoice_scheduler")


# Check once every hour
CHECK_INTERVAL_SECONDS = 60 * 60


# ============================================================
# HELPERS
# ============================================================


def _parse_date(value):
    """
    Parse an ISO date such as:
    2026-08-19

    Also supports an ISO datetime.
    """

    if not value:
        return None

    try:
        value = str(value)

        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()

    except (
        TypeError,
        ValueError,
    ):
        return None


def _invoice_total(invoice):
    """
    Calculate invoice total including tax.
    """

    total = 0.0

    for item in invoice.get(
        "items",
        [],
    ):
        try:
            quantity = float(
                item.get(
                    "quantity",
                    0,
                )
                or 0
            )

            unit_price = float(
                item.get(
                    "unit_price",
                    0,
                )
                or 0
            )

            tax_rate = float(
                item.get(
                    "tax_rate",
                    0,
                )
                or 0
            )

            subtotal = (
                quantity
                * unit_price
            )

            tax = (
                subtotal
                * tax_rate
                / 100
            )

            total += (
                subtotal
                + tax
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    return round(
        total,
        2,
    )


async def _get_notification_recipient(
    tenant_id,
):
    """
    Find the main user who should receive
    invoice notifications.
    """

    db = get_db()

    # --------------------------------------------------------
    # Try tenant owner
    # --------------------------------------------------------

    tenant = await db.tenants.find_one(
        {
            "id": tenant_id,
        },
        {
            "_id": 0,
            "owner_email": 1,
            "email": 1,
        },
    )

    if tenant:
        email = (
            tenant.get("owner_email")
            or tenant.get("email")
        )

        if email:
            return email

    # --------------------------------------------------------
    # Fallback to first tenant user
    # --------------------------------------------------------

    user = await db.users.find_one(
        {
            "tenant_id": tenant_id,
        },
        {
            "_id": 0,
            "email": 1,
        },
    )

    if user:
        return user.get("email")

    return None


async def _notification_exists(
    tenant_id,
    user_id,
    invoice_id,
    notification_type,
):
    """
    Prevent duplicate notifications.
    """

    db = get_db()

    return await db.notifications.find_one(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "entity_type": "invoice",
            "entity_id": invoice_id,
            "type": notification_type,
        }
    )


async def _create_notification(
    *,
    tenant_id,
    user_id,
    invoice,
    title,
    message,
    notification_type,
):
    """
    Create a single invoice notification
    if it does not already exist.
    """

    db = get_db()

    invoice_id = invoice.get("id")

    if not invoice_id:
        return False

    existing = await _notification_exists(
        tenant_id,
        user_id,
        invoice_id,
        notification_type,
    )

    if existing:
        return False

    notification_id = new_id()

    await db.notifications.insert_one(
        {
            "_id": notification_id,
            "id": notification_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "entity_type": "invoice",
            "entity_id": invoice_id,
            "url": "/finance",
            "read": False,
            "created_at": utcnow_iso(),
        }
    )

    return True


# ============================================================
# INVOICE REMINDER LOGIC
# ============================================================


async def process_invoice(
    invoice,
    today,
):
    """
    Process one invoice.

    Rules:

    7 days before:
        reminder

    3 days before:
        reminder

    1 day before:
        reminder

    Due today:
        reminder

    After due date:
        mark overdue + notification
    """

    db = get_db()

    invoice_id = invoice.get("id")
    tenant_id = invoice.get("tenant_id")

    if not invoice_id or not tenant_id:
        return {
            "updated": False,
            "notification": False,
        }

    status = invoice.get(
        "status",
        "draft",
    )

    # --------------------------------------------------------
    # Never touch these invoices
    # --------------------------------------------------------

    if status in {
        "paid",
        "cancelled",
    }:
        return {
            "updated": False,
            "notification": False,
        }

    due_date = _parse_date(
        invoice.get("due_date")
    )

    if not due_date:
        return {
            "updated": False,
            "notification": False,
        }

    days_until_due = (
        due_date - today
    ).days

    invoice_number = (
        invoice.get("number")
        or invoice_id
    )

    currency = (
        invoice.get("currency")
        or "EUR"
    )

    total = _invoice_total(
        invoice
    )

    recipient = await _get_notification_recipient(
        tenant_id
    )

    if not recipient:
        logger.warning(
            "No notification recipient "
            "found for tenant %s.",
            tenant_id,
        )

        return {
            "updated": False,
            "notification": False,
        }

    # ========================================================
    # OVERDUE
    # ========================================================

    if days_until_due < 0:

        # ----------------------------------------------------
        # Change status
        # ----------------------------------------------------

        updated = False

        if status != "overdue":

            result = await db.invoices.update_one(
                {
                    "id": invoice_id,
                    "tenant_id": tenant_id,
                    "status": {
                        "$nin": [
                            "paid",
                            "cancelled",
                            "overdue",
                        ]
                    },
                },
                {
                    "$set": {
                        "status": "overdue",
                        "updated_at": utcnow_iso(),
                    }
                },
            )

            updated = (
                result.modified_count > 0
            )

        # ----------------------------------------------------
        # Overdue notification
        # ----------------------------------------------------

        created = await _create_notification(
            tenant_id=tenant_id,
            user_id=recipient,
            invoice=invoice,
            title="Invoice overdue",
            message=(
                f"Invoice {invoice_number} "
                f"is overdue. "
                f"Amount: "
                f"{currency} "
                f"{total:,.2f}."
            ),
            notification_type=(
                "invoice_overdue"
            ),
        )

        return {
            "updated": updated,
            "notification": created,
        }

    # ========================================================
    # DUE TODAY
    # ========================================================

    if days_until_due == 0:

        created = await _create_notification(
            tenant_id=tenant_id,
            user_id=recipient,
            invoice=invoice,
            title="Invoice due today",
            message=(
                f"Invoice {invoice_number} "
                f"is due today. "
                f"Amount: "
                f"{currency} "
                f"{total:,.2f}."
            ),
            notification_type=(
                "invoice_due_today"
            ),
        )

        return {
            "updated": False,
            "notification": created,
        }

    # ========================================================
    # 1 DAY BEFORE
    # ========================================================

    if days_until_due == 1:

        created = await _create_notification(
            tenant_id=tenant_id,
            user_id=recipient,
            invoice=invoice,
            title="Invoice due tomorrow",
            message=(
                f"Invoice {invoice_number} "
                f"is due tomorrow. "
                f"Amount: "
                f"{currency} "
                f"{total:,.2f}."
            ),
            notification_type=(
                "invoice_due_tomorrow"
            ),
        )

        return {
            "updated": False,
            "notification": created,
        }

    # ========================================================
    # 3 DAYS BEFORE
    # ========================================================

    if days_until_due == 3:

        created = await _create_notification(
            tenant_id=tenant_id,
            user_id=recipient,
            invoice=invoice,
            title="Invoice due in 3 days",
            message=(
                f"Invoice {invoice_number} "
                f"is due in 3 days. "
                f"Amount: "
                f"{currency} "
                f"{total:,.2f}."
            ),
            notification_type=(
                "invoice_due_3_days"
            ),
        )

        return {
            "updated": False,
            "notification": created,
        }

    # ========================================================
    # 7 DAYS BEFORE
    # ========================================================

    if days_until_due == 7:

        created = await _create_notification(
            tenant_id=tenant_id,
            user_id=recipient,
            invoice=invoice,
            title="Invoice due in 7 days",
            message=(
                f"Invoice {invoice_number} "
                f"is due in 7 days. "
                f"Amount: "
                f"{currency} "
                f"{total:,.2f}."
            ),
            notification_type=(
                "invoice_due_7_days"
            ),
        )

        return {
            "updated": False,
            "notification": created,
        }

    return {
        "updated": False,
        "notification": False,
    }


# ============================================================
# CHECK ALL INVOICES
# ============================================================


async def check_invoices():
    """
    Check all open invoices.
    """

    db = get_db()

    today = datetime.now(
        timezone.utc
    ).date()

    invoices = await db.invoices.find(
        {
            "due_date": {
                "$ne": None,
            },
            "status": {
                "$nin": [
                    "paid",
                    "cancelled",
                ]
            },
        }
    ).to_list(
        length=5000
    )

    if not invoices:
        return

    updated_count = 0
    notification_count = 0

    for invoice in invoices:

        try:

            result = await process_invoice(
                invoice,
                today,
            )

            if result["updated"]:
                updated_count += 1

            if result["notification"]:
                notification_count += 1

        except Exception:
            logger.exception(
                "Failed processing invoice %s",
                invoice.get("id"),
            )

    if (
        updated_count
        or notification_count
    ):
        logger.info(
            "Invoice scheduler: "
            "%s invoices updated, "
            "%s notifications created.",
            updated_count,
            notification_count,
        )


# ============================================================
# SCHEDULER
# ============================================================


async def invoice_scheduler():
    """
    Run invoice processing periodically.
    """

    logger.info(
        "Invoice scheduler started."
    )

    while True:

        try:

            await check_invoices()

        except asyncio.CancelledError:

            logger.info(
                "Invoice scheduler stopped."
            )

            raise

        except Exception:

            logger.exception(
                "Invoice scheduler failed."
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )