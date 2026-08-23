"""Quote Approval → Invoice Flow.

Public share link so clients can view, accept or reject a quote without an
account. On accept, the quote can be converted to an invoice with one call,
and optionally spin up a project scaffold.

Email support:
- Send quote directly to CRM client's email
- Reuse/create public share token
- Track email delivery information
- Keep public quote approval flow unchanged
"""

import os
import secrets
import html

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import new_id, utcnow_iso
from app.core.email import send_html_email


router = APIRouter(
    prefix="/quotes",
    tags=["Quote Flow"],
    dependencies=[Depends(module_gate("finance"))],
)

public_router = APIRouter(
    prefix="/public/quotes",
    tags=["Public Quote"],
)


class DecisionIn(BaseModel):
    decision: str          # "accepted" | "rejected"
    comment: Optional[str] = None
    signer_name: Optional[str] = None


class ConvertRequest(BaseModel):
    create_project: bool = False


def _totals(items: list[dict]) -> dict:
    subtotal = sum(
        i.get("quantity", 0) * i.get("unit_price", 0)
        for i in items
    )

    tax = sum(
        (
            i.get("quantity", 0)
            * i.get("unit_price", 0)
        )
        * (i.get("tax_rate", 0) / 100)
        for i in items
    )

    return {
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(subtotal + tax, 2),
    }


# ============================================================
# SHARE QUOTE
# ============================================================

@router.post("/{qid}/share")
async def share_quote(qid: str, user: UserDep):
    db = get_db()

    q = await db.quotes.find_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        }
    )

    if not q:
        raise HTTPException(
            404,
            "Quote not found",
        )

    if q.get("status") in (
        "accepted",
        "rejected",
        "converted",
    ):
        raise HTTPException(
            409,
            f"Cannot share a quote that is already {q['status']}",
        )

    token = (
        q.get("share_token")
        or secrets.token_urlsafe(24)
    )

    now = utcnow_iso()

    await db.quotes.update_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "$set": {
                "share_token": token,
                "status": "sent",
                "sent_at": now,
                "updated_at": now,
            }
        },
    )

    base = os.environ.get(
        "FRONTEND_URL",
        "",
    ).rstrip("/")

    return {
        "share_token": token,
        "public_url": (
            f"{base}/public/quote/{token}"
        ),
    }


# ============================================================
# SEND QUOTE BY EMAIL
# ============================================================

@router.post("/{qid}/email")
async def email_quote(
    qid: str,
    user: UserDep,
):
    """
    Send a quote to the CRM client's email address.

    The email contains:
    - Client greeting
    - Quote number
    - Quote total
    - Public quote link
    - Button to view the quote

    The quote is marked as sent only after the email provider
    confirms successful delivery.
    """

    db = get_db()

    # --------------------------------------------------------
    # LOAD QUOTE
    # --------------------------------------------------------

    quote = await db.quotes.find_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "_id": 0,
        },
    )

    if not quote:
        raise HTTPException(
            status_code=404,
            detail="Quote not found",
        )

    if quote.get("status") in (
        "accepted",
        "rejected",
        "converted",
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot email a quote that is already "
                f"{quote['status']}"
            ),
        )

    # --------------------------------------------------------
    # LOAD CLIENT FROM CRM
    # --------------------------------------------------------

    client = {}

    if quote.get("client_id"):
        client = await db.clients.find_one(
            {
                "id": quote["client_id"],
                "tenant_id": user.tenant_id,
            },
            {
                "_id": 0,
            },
        ) or {}

    client_email = (
        client.get("email")
        or quote.get("client_email")
        or ""
    ).strip()

    if not client_email:
        raise HTTPException(
            status_code=400,
            detail=(
                "This client does not have an email address. "
                "Please add an email address to the CRM client first."
            ),
        )

    # --------------------------------------------------------
    # LOAD TENANT / COMPANY
    # --------------------------------------------------------

    tenant = await db.tenants.find_one(
        {
            "id": user.tenant_id,
        },
        {
            "_id": 0,
            "name": 1,
            "website": 1,
            "phone": 1,
            "email": 1,
            "address": 1,
            "logo_url": 1,
            "locale": 1,
            "language": 1,
            "currency": 1,
        },
    ) or {}

    company_name = (
        tenant.get("name")
        or "NED Tech CRM"
    )

    # --------------------------------------------------------
    # --------------------------------------------------------
    # PUBLIC LINK
    # --------------------------------------------------------

    share_token = (
        quote.get("share_token")
        or secrets.token_urlsafe(24)
    )

    public_base_url = settings.PUBLIC_URL

    if not public_base_url:
        raise HTTPException(
            status_code=500,
            detail="Public application URL is not configured.",
        )

    public_url = (
        f"{public_base_url}/public/quote/{share_token}"
    )

    # --------------------------------------------------------
    # QUOTE DATA
    # --------------------------------------------------------

    totals = _totals(
        quote.get("items", [])
    )

    currency = (
        quote.get("currency")
        or tenant.get("currency")
        or "EUR"
    )

    quote_number = (
        quote.get("number")
        or qid
    )

    client_name = (
        client.get("name")
        or quote.get("client_name")
        or "Customer"
    )

    # --------------------------------------------------------
    # HTML ESCAPING
    # --------------------------------------------------------

    safe_company = html.escape(
        str(company_name)
    )

    safe_client = html.escape(
        str(client_name)
    )

    safe_quote_number = html.escape(
        str(quote_number)
    )

    safe_currency = html.escape(
        str(currency)
    )

    safe_total = html.escape(
        f"{totals['total']:.2f}"
    )

    safe_public_url = html.escape(
        public_url,
        quote=True,
    )

    # --------------------------------------------------------
    # EMAIL LANGUAGE
    # --------------------------------------------------------

    requested_language = None
    try:
        requested_language = getattr(user, "language", None)
    except Exception:
        requested_language = None

    language = (
        quote.get("language")
        or quote.get("locale")
        or requested_language
        or tenant.get("locale")
        or tenant.get("language")
        or "en"
    )
    language = str(language).lower().replace("_", "-").split("-")[0]

    if language not in {"de", "en", "nl", "ar"}:
        language = "en"

    translations = {
        "en": {
            "greeting": "Hello",
            "intro": "Please find our quote",
            "quote": "QUOTE",
            "total": "TOTAL AMOUNT",
            "body": "You can view the quote online and submit your decision using the button below.",
            "cta": "View quote",
            "fallback": "If the button does not work, you can use this link:",
            "footer": "This email was sent by {company} via NED Tech CRM.",
            "subject": "Quote",
        },
        "de": {
            "greeting": "Guten Tag",
            "intro": "anbei erhalten Sie unser Angebot",
            "quote": "ANGEBOT",
            "total": "GESAMTBETRAG",
            "body": "Über den folgenden Button können Sie das Angebot online ansehen und Ihre Entscheidung abgeben.",
            "cta": "Angebot ansehen",
            "fallback": "Falls der Button nicht funktioniert, können Sie diesen Link verwenden:",
            "footer": "Diese E-Mail wurde von {company} über NED Tech CRM versendet.",
            "subject": "Angebot",
        },
        "nl": {
            "greeting": "Goedendag",
            "intro": "Hierbij ontvangt u onze offerte",
            "quote": "OFFERTE",
            "total": "TOTAALBEDRAG",
            "body": "Via de onderstaande knop kunt u de offerte online bekijken en uw beslissing doorgeven.",
            "cta": "Offerte bekijken",
            "fallback": "Als de knop niet werkt, kunt u deze link gebruiken:",
            "footer": "Deze e-mail is verzonden door {company} via NED Tech CRM.",
            "subject": "Offerte",
        },
        "ar": {
            "greeting": "مرحباً",
            "intro": "مرفق لكم عرض السعر الخاص بنا",
            "quote": "عرض السعر",
            "total": "المبلغ الإجمالي",
            "body": "يمكنكم عرض عرض السعر عبر الإنترنت وإرسال قراركم من خلال الزر أدناه.",
            "cta": "عرض عرض السعر",
            "fallback": "إذا لم يعمل الزر، يمكنكم استخدام الرابط التالي:",
            "footer": "تم إرسال هذا البريد الإلكتروني من {company} عبر NED Tech CRM.",
            "subject": "عرض سعر",
        },
    }[language]

    direction = "rtl" if language == "ar" else "ltr"
    text_align = "right" if language == "ar" else "left"

    safe_greeting = html.escape(translations["greeting"])
    safe_intro = html.escape(translations["intro"])
    safe_quote_label = html.escape(translations["quote"])
    safe_total_label = html.escape(translations["total"])
    safe_body = html.escape(translations["body"])
    safe_cta = html.escape(translations["cta"])
    safe_fallback = html.escape(translations["fallback"])
    safe_footer = html.escape(
        translations["footer"].format(company=company_name)
    )

    subject = (
        f"{company_name} – {translations['subject']} {quote_number}"
    )

    # --------------------------------------------------------
    # EMAIL HTML
    # --------------------------------------------------------

    email_html = f"""
<!DOCTYPE html>
<html lang="{language}" dir="{direction}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_quote_number}</title>
</head>

<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;color:#171717;">

    <div style="max-width:640px;margin:40px auto;background:#ffffff;border:1px solid #e5e5e5;border-radius:12px;overflow:hidden;direction:{direction};text-align:{text_align};">

        <div style="padding:28px 32px;border-bottom:1px solid #eeeeee;">
            <div style="font-size:20px;font-weight:700;letter-spacing:-0.3px;">
                {safe_company}
            </div>
        </div>

        <div style="padding:32px;">

            <p style="margin:0 0 20px;font-size:16px;">
                {safe_greeting} {safe_client},
            </p>

            <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#444444;">
                {safe_intro} <strong>{safe_quote_number}</strong>.
            </p>

            <div style="margin:24px 0;padding:20px;background:#f8f8f8;border-radius:8px;">
                <div style="font-size:12px;color:#777777;margin-bottom:6px;">
                    {safe_quote_label}
                </div>

                <div style="font-size:18px;font-weight:700;">
                    {safe_quote_number}
                </div>

                <div style="margin-top:16px;font-size:12px;color:#777777;margin-bottom:6px;">
                    {safe_total_label}
                </div>

                <div style="font-size:22px;font-weight:700;">
                    {safe_total} {safe_currency}
                </div>
            </div>

            <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#444444;">
                {safe_body}
            </p>

            <div style="text-align:center;margin:30px 0;">
                <a href="{safe_public_url}" style="display:inline-block;padding:14px 26px;background:#111111;color:#ffffff;text-decoration:none;border-radius:7px;font-size:15px;font-weight:600;">
                    {safe_cta}
                </a>
            </div>

            <p style="margin:24px 0 0;font-size:12px;line-height:1.5;color:#888888;">
                {safe_fallback}
            </p>

            <p style="margin:6px 0 0;font-size:12px;word-break:break-all;">
                <a href="{safe_public_url}" style="color:#555555;">
                    {safe_public_url}
                </a>
            </p>

        </div>

        <div style="padding:20px 32px;background:#fafafa;border-top:1px solid #eeeeee;font-size:12px;color:#888888;">
            {safe_footer}
        </div>

    </div>

</body>
</html>
"""

    # --------------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------------

    result = await send_html_email(
        to=client_email,
        subject=subject,
        html=email_html,
        reply_to=tenant.get("email"),
    )

    # --------------------------------------------------------
    # HANDLE EMAIL FAILURE
    # --------------------------------------------------------

    if not result.get("sent"):
        reason = result.get(
            "reason",
            "email_send_failed",
        )

        if reason == "email_not_configured":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Email service is not configured. "
                    "Please configure the email provider API key in backend .env."
                ),
            )

        if reason == "provider_error":
            raise HTTPException(
                status_code=502,
                detail=(
                    "The email provider rejected the email. "
                    "Please try again."
                ),
            )

        raise HTTPException(
            status_code=502,
            detail=(
                "The email could not be sent. "
                "Please try again."
            ),
        )

    # --------------------------------------------------------
    # SAVE EMAIL INFORMATION
    # --------------------------------------------------------

    now = utcnow_iso()

    await db.quotes.update_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "$set": {
                "share_token": share_token,

                "status": "sent",

                "sent_at": now,

                "email_sent_at": now,

                "email_sent_to": client_email,

                "email_provider_id": result.get("id"),

                "updated_at": now,
            }
        },
    )

    # --------------------------------------------------------
    # ACTIVITY LOG
    # --------------------------------------------------------

    await db.activities.insert_one(
        {
            "_id": new_id(),
            "id": new_id(),
            "tenant_id": user.tenant_id,
            "type": "quote_email_sent",
            "entity_id": qid,
            "message": (
                f"Quote {quote_number} emailed to "
                f"{client_email}"
            ),
            "actor": user.email,
            "created_at": now,
        }
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "sent": True,
        "email": client_email,
        "quote_id": qid,
        "quote_number": quote_number,
        "public_url": public_url,
        "email_id": result.get("id"),
    }


# ============================================================
# GET QUOTE
# ============================================================

@router.get("/{qid}")
async def get_quote(
    qid: str,
    user: UserDep,
):
    db = get_db()

    q = await db.quotes.find_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "_id": 0,
        },
    )

    if not q:
        raise HTTPException(
            404,
            "Quote not found",
        )

    q["totals"] = _totals(
        q.get("items", [])
    )

    return q


# ============================================================
# PUBLIC GET QUOTE
# ============================================================

@public_router.get("/{token}")
async def public_get_quote(
    token: str,
):
    db = get_db()

    q = await db.quotes.find_one(
        {
            "share_token": token,
        },
        {
            "_id": 0,
        },
    )

    if not q:
        raise HTTPException(
            404,
            "Quote not found",
        )

    q["totals"] = _totals(
        q.get("items", [])
    )

    tenant = await db.tenants.find_one(
        {
            "id": q["tenant_id"],
        },
        {
            "_id": 0,
            "modules": 0,
        },
    ) or {}

    return {
        "quote": q,
        "tenant": {
            "name": tenant.get("name"),
            "logo_url": tenant.get("logo_url"),
            "address": tenant.get("address"),
            "website": tenant.get("website"),
            "currency": tenant.get("currency"),
        },
    }


# ============================================================
# PUBLIC QUOTE DECISION
# ============================================================

@public_router.post("/{token}/decision")
async def public_decide(
    token: str,
    body: DecisionIn,
):
    if body.decision not in (
        "accepted",
        "rejected",
    ):
        raise HTTPException(
            400,
            "decision must be 'accepted' or 'rejected'",
        )

    db = get_db()

    q = await db.quotes.find_one(
        {
            "share_token": token,
        }
    )

    if not q:
        raise HTTPException(
            404,
            "Quote not found",
        )

    if q.get("status") in (
        "accepted",
        "rejected",
        "converted",
    ):
        raise HTTPException(
            409,
            f"Quote already {q['status']}",
        )

    now = utcnow_iso()

    await db.quotes.update_one(
        {
            "id": q["id"],
        },
        {
            "$set": {
                "status": body.decision,
                "decision_comment": body.comment,
                "signer_name": body.signer_name,
                "decided_at": now,
                "updated_at": now,
            }
        },
    )

    await db.activities.insert_one(
        {
            "_id": new_id(),
            "id": new_id(),
            "tenant_id": q["tenant_id"],
            "type": f"quote_{body.decision}",
            "entity_id": q["id"],
            "message": (
                f"Quote {q.get('number', '')} "
                f"{body.decision}"
                + (
                    f" by {body.signer_name}"
                    if body.signer_name
                    else ""
                )
            ),
            "actor": body.signer_name or "client",
            "created_at": now,
        }
    )

    return {
        "ok": True,
        "status": body.decision,
    }


# ============================================================
# CONVERT QUOTE → INVOICE
# ============================================================

@router.post(
    "/{qid}/convert",
    status_code=201,
)
async def convert_quote_to_invoice(
    qid: str,
    body: ConvertRequest,
    user: UserDep,
):
    db = get_db()

    q = await db.quotes.find_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "_id": 0,
        },
    )

    if not q:
        raise HTTPException(
            404,
            "Quote not found",
        )

    if (
        q.get("converted_invoice_id")
        or q.get("status") == "converted"
    ):
        raise HTTPException(
            409,
            "Already converted",
        )

    if q.get("status") != "accepted":
        raise HTTPException(
            400,
            "Only accepted quotes can be converted",
        )

    # --------------------------------------------------------
    # CREATE INVOICE
    # --------------------------------------------------------

    inv_count = await db.invoices.count_documents(
        {
            "tenant_id": user.tenant_id,
        }
    )

    inv_id = new_id()

    now = utcnow_iso()

    invoice = {
        "_id": inv_id,
        "id": inv_id,
        "tenant_id": user.tenant_id,

        "number": f"INV-{inv_count + 1:05d}",

        "client_id": q.get("client_id"),
        "client_name": q.get("client_name"),

        "issue_date": now[:10],
        "due_date": None,

        "currency": q.get(
            "currency",
            "USD",
        ),

        "items": q.get(
            "items",
            [],
        ),

        "status": "draft",

        "notes": q.get(
            "notes"
        ),

        "source_quote_id": q["id"],

        "created_at": now,
        "updated_at": now,
    }

    await db.invoices.insert_one(
        invoice
    )

    # --------------------------------------------------------
    # OPTIONAL PROJECT
    # --------------------------------------------------------

    project_id = None

    if body.create_project:
        project_id = new_id()

        await db.projects.insert_one(
            {
                "_id": project_id,
                "id": project_id,
                "tenant_id": user.tenant_id,

                "name": (
                    f"{q.get('client_name', 'Client')} "
                    f"— "
                    f"{q.get('number', 'Project')}"
                ),

                "client_id": q.get(
                    "client_id"
                ),

                "status": "active",

                "color": "#171717",

                "description": q.get(
                    "notes"
                ),

                "source_quote_id": q["id"],

                "created_at": now,
                "updated_at": now,
            }
        )

    # --------------------------------------------------------
    # MARK QUOTE AS CONVERTED
    # --------------------------------------------------------

    await db.quotes.update_one(
        {
            "tenant_id": user.tenant_id,
            "id": qid,
        },
        {
            "$set": {
                "converted_invoice_id": inv_id,
                "converted_project_id": project_id,
                "status": "converted",
                "updated_at": now,
            }
        },
    )

    return {
        "invoice_id": inv_id,
        "project_id": project_id,
    }