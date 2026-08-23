"""Finance: quotes, invoices, expenses. Simple PDF export via reportlab."""

from typing import Optional
from io import BytesIO

import base64
from datetime import datetime, timezone
from app.core.email import send_html_email
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import (
    BaseRepository,
    new_id,
    utcnow_iso,
)


router = APIRouter(
    tags=["Finance"],
    dependencies=[
        Depends(module_gate("finance")),
        Depends(require_permission("finance")),
    ],
)


# ============================================================
# MODELS
# ============================================================


class LineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float = 0
    tax_rate: float = 0


class InvoiceIn(BaseModel):
    number: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "USD"
    items: list[LineItem] = Field(default_factory=list)
    notes: Optional[str] = None
    status: str = "draft"


class QuoteIn(InvoiceIn):
    status: str = "draft"


class ExpenseIn(BaseModel):
    date: Optional[str] = None
    category: str = "general"
    vendor: Optional[str] = None
    amount: float = 0
    currency: str = "USD"
    tax_rate: float = 0
    description: Optional[str] = None
    receipt_url: Optional[str] = None


# ============================================================
# REPOSITORIES
# ============================================================


_invoices: BaseRepository | None = None
_quotes: BaseRepository | None = None
_expenses: BaseRepository | None = None


def _r_inv() -> BaseRepository:
    global _invoices

    if _invoices is None:
        _invoices = BaseRepository(
            get_db(),
            InvoiceIn,
            "invoices",
        )

    return _invoices


def _r_q() -> BaseRepository:
    global _quotes

    if _quotes is None:
        _quotes = BaseRepository(
            get_db(),
            QuoteIn,
            "quotes",
        )

    return _quotes


def _r_e() -> BaseRepository:
    global _expenses

    if _expenses is None:
        _expenses = BaseRepository(
            get_db(),
            ExpenseIn,
            "expenses",
        )

    return _expenses


# ============================================================
# HELPERS
# ============================================================


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


async def _create_invoice_notification(
    *,
    tenant_id: str,
    user_id: str,
    title: str,
    message: str,
    invoice_id: str,
    notification_type: str,
):
    """
    Create an in-app notification for an invoice.

    Notifications are stored in the same collection used by
    the global NotificationBell component.
    """

    notification_id = new_id()

    await get_db().notifications.insert_one(
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


# ============================================================
# INVOICES
# ============================================================


@router.get("/invoices")
async def list_invoices(
    user: UserDep,
):
    docs = await _r_inv().list(
        user.tenant_id,
        limit=500,
    )

    for doc in docs:
        doc["totals"] = _totals(
            doc.get("items", [])
        )

    return docs


@router.post(
    "/invoices",
    status_code=201,
)
async def create_invoice(
    body: InvoiceIn,
    user: UserDep,
):
    data = body.model_dump()

    if not data.get("number"):
        count = await _r_inv().count(
            user.tenant_id
        )

        data["number"] = f"INV-{count + 1:05d}"

    doc = await _r_inv().create(
        user.tenant_id,
        data,
    )

    doc["totals"] = _totals(
        doc.get("items", [])
    )

    total = doc["totals"]["total"]
    currency = doc.get("currency") or "EUR"

    await _create_invoice_notification(
        tenant_id=user.tenant_id,
        user_id=user.email,
        title="Invoice created",
        message=(
            f"Invoice {doc['number']} "
            f"was created for "
            f"{currency} {total:,.2f}."
        ),
        invoice_id=doc["id"],
        notification_type="invoice_created",
    )

    return doc


@router.get("/invoices/{iid}")
async def get_invoice(
    iid: str,
    user: UserDep,
):
    doc = await _r_inv().get(
        user.tenant_id,
        iid,
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    doc["totals"] = _totals(
        doc.get("items", [])
    )

    return doc


@router.patch("/invoices/{iid}")
async def update_invoice(
    iid: str,
    body: InvoiceIn,
    user: UserDep,
):
    old_doc = await _r_inv().get(
        user.tenant_id,
        iid,
    )

    if not old_doc:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    doc = await _r_inv().update(
        user.tenant_id,
        iid,
        body.model_dump(),
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    doc["totals"] = _totals(
        doc.get("items", [])
    )

    old_status = old_doc.get("status")
    new_status = doc.get("status")

    if old_status != new_status:
        total = doc["totals"]["total"]
        currency = doc.get("currency") or "EUR"
        number = doc.get("number") or iid

        notification_map = {
            "sent": (
                "Invoice sent",
                (
                    f"Invoice {number} "
                    f"has been marked as sent."
                ),
                "invoice_sent",
            ),
            "paid": (
                "Invoice paid",
                (
                    f"Invoice {number} "
                    f"has been marked as paid "
                    f"({currency} {total:,.2f})."
                ),
                "invoice_paid",
            ),
            "overdue": (
                "Invoice overdue",
                (
                    f"Invoice {number} "
                    f"is now overdue "
                    f"({currency} {total:,.2f})."
                ),
                "invoice_overdue",
            ),
            "cancelled": (
                "Invoice cancelled",
                (
                    f"Invoice {number} "
                    f"has been cancelled."
                ),
                "invoice_cancelled",
            ),
        }

        notification = notification_map.get(
            new_status
        )

        if notification:
            (
                title,
                message,
                notification_type,
            ) = notification

            await _create_invoice_notification(
                tenant_id=user.tenant_id,
                user_id=user.email,
                title=title,
                message=message,
                invoice_id=doc["id"],
                notification_type=notification_type,
            )

    return doc


@router.delete(
    "/invoices/{iid}",
    status_code=204,
)
async def delete_invoice(
    iid: str,
    user: UserDep,
):
    await _r_inv().delete(
        user.tenant_id,
        iid,
    )

    return None


# ============================================================
# INVOICE PDF
# ============================================================


@router.get("/invoices/{iid}/pdf")
async def invoice_pdf(
    iid: str,
    user: UserDep,
    lang: str | None = Query(None),
):
    invoice = await _r_inv().get(
        user.tenant_id,
        iid,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    tenant = await get_db().tenants.find_one(
        {"id": user.tenant_id},
        {"_id": 0},
    ) or {}

    client = {}

    if invoice.get("client_id"):
        client = await get_db().clients.find_one(
            {
                "id": invoice["client_id"],
                "tenant_id": user.tenant_id,
            },
            {"_id": 0},
        ) or {}

    pdf_language = (
        lang
        or tenant.get("locale")
        or tenant.get("language")
        or "en"
    )

    pdf = _render_invoice_pdf(
        invoice,
        tenant,
        client,
        pdf_language,
    )

    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="{invoice.get("number", "invoice")}.pdf"'
            )
        },
    )


# ============================================================
# INVOICE PDF RENDERER
# ============================================================


def _render_invoice_pdf(
    invoice: dict,
    tenant: dict,
    client: dict,
    lang: str = "en",
) -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import (
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()

    PAGE_WIDTH, PAGE_HEIGHT = A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=34 * mm,
        title=invoice.get("number", "Invoice"),
        author=tenant.get("name", "Company"),
    )

    DARK = colors.HexColor("#171717")
    TEXT = colors.HexColor("#242424")
    MUTED = colors.HexColor("#6B7280")
    BORDER = colors.HexColor("#E5E7EB")
    LIGHT = colors.HexColor("#F7F7F7")
    WHITE = colors.white

    base = getSampleStyleSheet()

    company_style = ParagraphStyle(
        "InvoiceCompany",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=DARK,
    )

    invoice_title = ParagraphStyle(
        "InvoiceTitle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=28,
        alignment=TA_RIGHT,
        textColor=DARK,
    )

    meta_value = ParagraphStyle(
        "MetaValue",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_RIGHT,
        textColor=TEXT,
    )

    section = ParagraphStyle(
        "Section",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=MUTED,
    )

    body = ParagraphStyle(
        "Body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=TEXT,
    )

    body_right = ParagraphStyle(
        "BodyRight",
        parent=body,
        alignment=TA_RIGHT,
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=WHITE,
    )

    table_header_right = ParagraphStyle(
        "TableHeaderRight",
        parent=table_header,
        alignment=TA_RIGHT,
    )

    small = ParagraphStyle(
        "Small",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
    )

    total_label = ParagraphStyle(
        "TotalLabel",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK,
    )

    total_value = ParagraphStyle(
        "TotalValue",
        parent=body_right,
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=DARK,
    )

    def safe(value):
        if value is None:
            return ""

        return escape(str(value))

    def money(value):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "0.00"

    def first_value(*values):
        for value in values:
            if value not in (None, ""):
                return value

        return ""

    locale = str(
        lang
        or tenant.get("locale")
        or tenant.get("language")
        or "en"
    )

    locale = (
        locale
        .lower()
        .replace("_", "-")
        .split("-")[0]
    )

    if locale not in {"nl", "de", "en"}:
        locale = "en"

    L = {
        "en": {
            "invoice": "INVOICE",
            "invoice_no": "Invoice #",
            "issue_date": "Issue date",
            "due_date": "Due date",
            "bill_to": "BILL TO",
            "description": "Description",
            "qty": "Qty",
            "unit_price": "Unit price",
            "vat": "VAT",
            "amount": "Amount",
            "subtotal": "Subtotal",
            "total": "TOTAL",
            "payment": "PAYMENT INFORMATION",
            "account_holder": "Account holder",
            "address": "Address",
            "iban": "IBAN",
            "tel": "Phone",
            "website": "Website",
            "kvk": "Chamber of Commerce No.",
            "vat_id": "VAT ID",
            "notes": "Notes",
            "page": "Page",
        },
        "nl": {
            "invoice": "FACTUUR",
            "invoice_no": "Factuurnummer",
            "issue_date": "Factuurdatum",
            "due_date": "Vervaldatum",
            "bill_to": "FACTUUR AAN",
            "description": "Omschrijving",
            "qty": "Aantal",
            "unit_price": "Prijs per eenheid",
            "vat": "BTW",
            "amount": "Bedrag",
            "subtotal": "Subtotaal",
            "total": "TOTAAL",
            "payment": "BETALINGSINFORMATIE",
            "account_holder": "Rekeninghouder",
            "address": "Adres",
            "iban": "IBAN",
            "tel": "Telefoon",
            "website": "Website",
            "kvk": "KVK",
            "vat_id": "BTW",
            "notes": "Notities",
            "page": "Pagina",
        },
        "de": {
            "invoice": "RECHNUNG",
            "invoice_no": "Rechnungsnummer",
            "issue_date": "Rechnungsdatum",
            "due_date": "Fälligkeitsdatum",
            "bill_to": "RECHNUNGSEMPFÄNGER",
            "description": "Beschreibung",
            "qty": "Menge",
            "unit_price": "Einzelpreis",
            "vat": "MwSt.",
            "amount": "Betrag",
            "subtotal": "Zwischensumme",
            "total": "GESAMT",
            "payment": "ZAHLUNGSINFORMATIONEN",
            "account_holder": "Kontoinhaber",
            "address": "Adresse",
            "iban": "IBAN",
            "tel": "Telefon",
            "website": "Website",
            "kvk": "Handelsregisternr.",
            "vat_id": "USt-IdNr.",
            "notes": "Notizen",
            "page": "Seite",
        },
    }[locale]

    company_name = tenant.get("name") or "Company"
    company_address = tenant.get("address") or ""
    company_phone = tenant.get("phone") or ""
    company_website = tenant.get("website") or ""
    company_iban = tenant.get("iban") or ""
    company_kvk = tenant.get("kvk_number") or ""
    company_vat = tenant.get("vat_number") or ""

    invoice_number = invoice.get("number") or ""
    issue_date = invoice.get("issue_date") or ""
    due_date = invoice.get("due_date") or ""

    currency = (
        invoice.get("currency")
        or tenant.get("currency")
        or "EUR"
    )

    client_name = first_value(
        client.get("name"),
        invoice.get("client_name"),
    )

    client_company = client.get("company") or ""
    client_contact = client.get("contact_person") or ""
    client_address = client.get("address") or ""
    client_email = client.get("email") or ""
    client_phone = client.get("phone") or ""
    client_vat = client.get("vat_number") or ""

    story = []

    company_block = [
        Paragraph(
            safe(company_name),
            company_style,
        )
    ]

    if company_address:
        company_block.append(
            Paragraph(
                safe(company_address),
                small,
            )
        )

    if company_phone:
        company_block.append(
            Paragraph(
                f"{L['tel']}: {safe(company_phone)}",
                small,
            )
        )

    if company_website:
        company_block.append(
            Paragraph(
                safe(company_website),
                small,
            )
        )

    invoice_block = [
        Paragraph(
            L["invoice"],
            invoice_title,
        ),
        Spacer(1, 4),
        Paragraph(
            f"<b>{L['invoice_no']}</b>&nbsp;&nbsp;"
            f"{safe(invoice_number)}",
            meta_value,
        ),
        Paragraph(
            f"<b>{L['issue_date']}</b>&nbsp;&nbsp;"
            f"{safe(issue_date)}",
            meta_value,
        ),
        Paragraph(
            f"<b>{L['due_date']}</b>&nbsp;&nbsp;"
            f"{safe(due_date)}",
            meta_value,
        ),
    ]

    header = Table(
        [[company_block, invoice_block]],
        colWidths=[
            88 * mm,
            89 * mm,
        ],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(header)
    story.append(Spacer(1, 8))

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=DARK,
            spaceBefore=2,
            spaceAfter=16,
        )
    )

    bill_to = [
        Paragraph(
            L["bill_to"],
            section,
        ),
        Spacer(1, 4),
    ]

    if client_company:
        bill_to.append(
            Paragraph(
                f"<b>{safe(client_company)}</b>",
                body,
            )
        )

    if client_name:
        bill_to.append(
            Paragraph(
                safe(client_name),
                body,
            )
        )

    if client_contact:
        bill_to.append(
            Paragraph(
                safe(client_contact),
                small,
            )
        )

    if client_address:
        bill_to.append(
            Paragraph(
                safe(client_address),
                small,
            )
        )

    if client_email:
        bill_to.append(
            Paragraph(
                safe(client_email),
                small,
            )
        )

    if client_phone:
        bill_to.append(
            Paragraph(
                safe(client_phone),
                small,
            )
        )

    if client_vat:
        bill_to.append(
            Paragraph(
                f"{L['vat']}: {safe(client_vat)}",
                small,
            )
        )

    bill_to_table = Table(
        [[bill_to]],
        colWidths=[
            177 * mm
        ],
    )

    bill_to_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(bill_to_table)
    story.append(Spacer(1, 18))

    item_rows = [
        [
            Paragraph(
                L["description"],
                table_header,
            ),
            Paragraph(
                L["qty"],
                table_header_right,
            ),
            Paragraph(
                L["unit_price"],
                table_header_right,
            ),
            Paragraph(
                L["vat"],
                table_header_right,
            ),
            Paragraph(
                L["amount"],
                table_header_right,
            ),
        ]
    ]

    for item in invoice.get("items", []):
        quantity = item.get("quantity", 0) or 0
        unit_price = item.get("unit_price", 0) or 0
        tax_rate = item.get("tax_rate", 0) or 0

        try:
            amount = (
                float(quantity)
                * float(unit_price)
            )
        except (TypeError, ValueError):
            amount = 0

        item_rows.append(
            [
                Paragraph(
                    safe(
                        item.get(
                            "description",
                            "",
                        )
                    ),
                    body,
                ),
                Paragraph(
                    safe(quantity),
                    body_right,
                ),
                Paragraph(
                    f"{safe(currency)} "
                    f"{money(unit_price)}",
                    body_right,
                ),
                Paragraph(
                    f"{float(tax_rate):.1f}%",
                    body_right,
                ),
                Paragraph(
                    f"{safe(currency)} "
                    f"{money(amount)}",
                    body_right,
                ),
            ]
        )

    items_table = Table(
        item_rows,
        colWidths=[
            78 * mm,
            18 * mm,
            28 * mm,
            20 * mm,
            33 * mm,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )

    items_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    DARK,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    WHITE,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.8,
                    DARK,
                ),
                (
                    "LINEBELOW",
                    (0, 1),
                    (-1, -1),
                    0.4,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 1),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, -1),
                    7,
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "RIGHT",
                ),
            ]
        )
    )

    story.append(items_table)
    story.append(Spacer(1, 16))

    totals = _totals(
        invoice.get("items", [])
    )

    totals_rows = [
        [
            "",
            Paragraph(
                L["subtotal"],
                body,
            ),
            Paragraph(
                f"{safe(currency)} "
                f"{money(totals['subtotal'])}",
                body_right,
            ),
        ],
        [
            "",
            Paragraph(
                L["vat"],
                body,
            ),
            Paragraph(
                f"{safe(currency)} "
                f"{money(totals['tax'])}",
                body_right,
            ),
        ],
        [
            "",
            Paragraph(
                f"<b>{L['total']}</b>",
                total_label,
            ),
            Paragraph(
                f"<b>{safe(currency)} "
                f"{money(totals['total'])}</b>",
                total_value,
            ),
        ],
    ]

    totals_table = Table(
        totals_rows,
        colWidths=[
            94 * mm,
            40 * mm,
            43 * mm,
        ],
        hAlign="RIGHT",
    )

    totals_table.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 2),
                    (-1, 2),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 2),
                    (-1, 2),
                    8,
                ),
                (
                    "LINEABOVE",
                    (1, 2),
                    (-1, 2),
                    1.2,
                    DARK,
                ),
            ]
        )
    )

    story.append(totals_table)

    if company_iban:
        story.append(Spacer(1, 18))

        payment_block = [
            Paragraph(
                L["payment"],
                section,
            ),
            Spacer(1, 5),
        ]

        if company_name:
            payment_block.append(
                Paragraph(
                    f"<b>{L['account_holder']}:</b> "
                    f"{safe(company_name)}",
                    body,
                )
            )

        if company_address:
            payment_block.append(
                Paragraph(
                    f"<b>{L['address']}:</b> "
                    f"{safe(company_address)}",
                    body,
                )
            )

        if company_iban:
            payment_block.append(
                Paragraph(
                    f"<b>{L['iban']}:</b> "
                    f"{safe(company_iban)}",
                    body,
                )
            )

        if company_phone:
            payment_block.append(
                Paragraph(
                    f"<b>{L['tel']}:</b> "
                    f"{safe(company_phone)}",
                    body,
                )
            )

        if company_website:
            payment_block.append(
                Paragraph(
                    f"<b>{L['website']}:</b> "
                    f"{safe(company_website)}",
                    body,
                )
            )

        payment_table = Table(
            [[payment_block]],
            colWidths=[
                177 * mm
            ],
        )

        payment_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#FAFAFA"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        BORDER,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        story.append(payment_table)

    if invoice.get("notes"):
        story.append(Spacer(1, 14))

        story.append(
            Paragraph(
                f"<b>{L['notes']}</b>",
                section,
            )
        )

        story.append(Spacer(1, 4))

        story.append(
            Paragraph(
                safe(invoice["notes"]),
                small,
            )
        )

    def draw_footer(
        canvas,
        doc,
    ):
        canvas.saveState()

        footer_y = 10 * mm

        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)

        canvas.line(
            doc.leftMargin,
            footer_y + 18,
            PAGE_WIDTH - doc.rightMargin,
            footer_y + 18,
        )

        canvas.setFont(
            "Helvetica-Bold",
            7.5,
        )

        canvas.setFillColor(TEXT)

        canvas.drawString(
            doc.leftMargin,
            footer_y + 8,
            str(company_name),
        )

        canvas.setFont(
            "Helvetica",
            6.7,
        )

        canvas.setFillColor(MUTED)

        footer_left = []

        if company_address:
            footer_left.append(
                str(company_address)
            )

        if company_phone:
            footer_left.append(
                f"{L['tel']}: {company_phone}"
            )

        if company_website:
            footer_left.append(
                str(company_website)
            )

        footer_line = "  |  ".join(
            footer_left
        )

        if footer_line:
            canvas.drawString(
                doc.leftMargin,
                footer_y - 2,
                footer_line,
            )

        footer_right = []

        if company_iban:
            footer_right.append(
                f"IBAN: {company_iban}"
            )

        if company_kvk:
            footer_right.append(
                f"{L['kvk']}: {company_kvk}"
            )

        if company_vat:
            footer_right.append(
                f"{L['vat_id']}: {company_vat}"
            )

        legal_line = "  |  ".join(
            footer_right
        )

        if legal_line:
            canvas.drawRightString(
                PAGE_WIDTH - doc.rightMargin,
                footer_y + 8,
                legal_line,
            )

        canvas.setFont(
            "Helvetica",
            6.7,
        )

        canvas.setFillColor(MUTED)

        canvas.drawRightString(
            PAGE_WIDTH - doc.rightMargin,
            footer_y - 12,
            f"{L['page']} "
            f"{canvas.getPageNumber()}",
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    return buffer.getvalue()


# ============================================================
# QUOTES
# ============================================================


def _quote_language(tenant: dict) -> str:
    """
    Determine the quote language from tenant settings.

    Supported:
    - de = German
    - nl = Dutch
    - en = English

    Defaults to German because the primary market includes Germany.
    """
    value = (
        tenant.get("language")
        or tenant.get("locale")
        or "de"
    )

    value = str(value).lower().strip()

    if value.startswith("nl"):
        return "nl"

    if value.startswith("en"):
        return "en"

    return "de"


def _render_quote_pdf(
    quote: dict,
    tenant: dict,
    client: dict,
) -> bytes:
    """
    Generate a professional A4 PDF for a quotation / offer.
    """

    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import (
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
    )

    locale = _quote_language(tenant)

    translations = {
        "de": {
            "title": "ANGEBOT",
            "number": "Angebotsnummer",
            "issue_date": "Ausstellungsdatum",
            "valid_until": "Gültig bis",
            "customer": "KUNDE",
            "description": "Beschreibung",
            "quantity": "Menge",
            "unit_price": "Einzelpreis",
            "vat": "MwSt.",
            "amount": "Betrag",
            "subtotal": "Zwischensumme",
            "total": "GESAMT",
            "notes": "Notizen",
            "contact": "Kontakt",
            "phone": "Telefon",
            "email": "E-Mail",
            "website": "Website",
            "vat_id": "USt-IdNr.",
            "kvk": "Handelsregisternr.",
            "offer_text": "Vielen Dank für Ihre Anfrage. Gerne unterbreiten wir Ihnen folgendes Angebot.",
        },
        "nl": {
            "title": "OFFERTE",
            "number": "Offertenummer",
            "issue_date": "Datum",
            "valid_until": "Geldig tot",
            "customer": "KLANT",
            "description": "Omschrijving",
            "quantity": "Aantal",
            "unit_price": "Prijs per stuk",
            "vat": "BTW",
            "amount": "Bedrag",
            "subtotal": "Subtotaal",
            "total": "TOTAAL",
            "notes": "Notities",
            "contact": "Contact",
            "phone": "Telefoon",
            "email": "E-mail",
            "website": "Website",
            "vat_id": "BTW-nummer",
            "kvk": "KvK-nummer",
            "offer_text": "Bedankt voor uw aanvraag. Graag doen wij u hierbij de volgende offerte.",
        },
        "en": {
            "title": "QUOTATION",
            "number": "Quote number",
            "issue_date": "Issue date",
            "valid_until": "Valid until",
            "customer": "CUSTOMER",
            "description": "Description",
            "quantity": "Quantity",
            "unit_price": "Unit price",
            "vat": "VAT",
            "amount": "Amount",
            "subtotal": "Subtotal",
            "total": "TOTAL",
            "notes": "Notes",
            "contact": "Contact",
            "phone": "Phone",
            "email": "Email",
            "website": "Website",
            "vat_id": "VAT ID",
            "kvk": "Registration no.",
            "offer_text": "Thank you for your inquiry. We are pleased to provide you with the following quotation.",
        },
    }

    L = translations[locale]

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def safe(value) -> str:
        if value is None:
            return ""

        return escape(
            str(value)
        )

    def money(value) -> str:
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return "0.00"

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    company_name = (
        tenant.get("name")
        or "NED Tech"
    )

    company_address = (
        tenant.get("address")
        or ""
    )

    company_phone = (
        tenant.get("phone")
        or ""
    )

    company_email = (
        tenant.get("email")
        or tenant.get("contact_email")
        or ""
    )

    company_website = (
        tenant.get("website")
        or ""
    )

    company_vat = (
        tenant.get("vat_number")
        or ""
    )

    company_kvk = (
        tenant.get("kvk_number")
        or ""
    )

    company_iban = (
        tenant.get("iban")
        or ""
    )

    # --------------------------------------------------------
    # Quote
    # --------------------------------------------------------

    quote_number = (
        quote.get("number")
        or ""
    )

    issue_date = (
        quote.get("issue_date")
        or ""
    )

    valid_until = (
        quote.get("due_date")
        or quote.get("valid_until")
        or ""
    )

    currency = (
        quote.get("currency")
        or tenant.get("currency")
        or "EUR"
    )

    client_name = (
        client.get("name")
        or quote.get("client_name")
        or ""
    )

    client_company = (
        client.get("company")
        or ""
    )

    client_contact = (
        client.get("contact_person")
        or ""
    )

    client_address = (
        client.get("address")
        or ""
    )

    client_email = (
        client.get("email")
        or ""
    )

    client_phone = (
        client.get("phone")
        or ""
    )

    client_vat = (
        client.get("vat_number")
        or ""
    )

    # --------------------------------------------------------
    # PDF styles
    # --------------------------------------------------------

    styles = getSampleStyleSheet()

    company_style = ParagraphStyle(
        "QuoteCompany",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#111111"),
    )

    title_style = ParagraphStyle(
        "QuoteTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=27,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#111111"),
    )

    meta_style = ParagraphStyle(
        "QuoteMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#555555"),
    )

    section_style = ParagraphStyle(
        "QuoteSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#777777"),
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "QuoteBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )

    small_style = ParagraphStyle(
        "QuoteSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#666666"),
    )

    table_header_style = ParagraphStyle(
        "QuoteTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    table_body_style = ParagraphStyle(
        "QuoteTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#222222"),
    )

    total_style = ParagraphStyle(
        "QuoteTotal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#111111"),
    )

    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"{L['title']} {quote_number}",
        author=company_name,
    )

    story = []

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    company_block = [
        Paragraph(
            safe(company_name),
            company_style,
        )
    ]

    if company_address:
        company_block.append(
            Paragraph(
                safe(company_address),
                small_style,
            )
        )

    if company_phone:
        company_block.append(
            Paragraph(
                f"{L['phone']}: {safe(company_phone)}",
                small_style,
            )
        )

    if company_email:
        company_block.append(
            Paragraph(
                f"{L['email']}: {safe(company_email)}",
                small_style,
            )
        )

    if company_website:
        company_block.append(
            Paragraph(
                safe(company_website),
                small_style,
            )
        )

    quote_block = [
        Paragraph(
            L["title"],
            title_style,
        ),
        Spacer(1, 4),
        Paragraph(
            f"<b>{safe(L['number'])}</b>&nbsp;&nbsp;"
            f"{safe(quote_number)}",
            meta_style,
        ),
        Paragraph(
            f"<b>{safe(L['issue_date'])}</b>&nbsp;&nbsp;"
            f"{safe(issue_date)}",
            meta_style,
        ),
    ]

    if valid_until:
        quote_block.append(
            Paragraph(
                f"<b>{safe(L['valid_until'])}</b>&nbsp;&nbsp;"
                f"{safe(valid_until)}",
                meta_style,
            )
        )

    header = Table(
        [[
            company_block,
            quote_block,
        ]],
        colWidths=[
            88 * mm,
            89 * mm,
        ],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(header)

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#222222"),
            spaceBefore=2,
            spaceAfter=14,
        )
    )

    # --------------------------------------------------------
    # Customer
    # --------------------------------------------------------

    customer_block = [
        Paragraph(
            L["customer"],
            section_style,
        ),
        Spacer(1, 3),
    ]

    if client_company:
        customer_block.append(
            Paragraph(
                f"<b>{safe(client_company)}</b>",
                body_style,
            )
        )

    if client_name:
        customer_block.append(
            Paragraph(
                safe(client_name),
                body_style,
            )
        )

    if client_contact:
        customer_block.append(
            Paragraph(
                safe(client_contact),
                small_style,
            )
        )

    if client_address:
        customer_block.append(
            Paragraph(
                safe(client_address),
                small_style,
            )
        )

    if client_email:
        customer_block.append(
            Paragraph(
                safe(client_email),
                small_style,
            )
        )

    if client_phone:
        customer_block.append(
            Paragraph(
                safe(client_phone),
                small_style,
            )
        )

    if client_vat:
        customer_block.append(
            Paragraph(
                f"{L['vat_id']}: {safe(client_vat)}",
                small_style,
            )
        )

    customer_table = Table(
        [[customer_block]],
        colWidths=[
            177 * mm
        ],
    )

    customer_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F7F7F7"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#DDDDDD"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(customer_table)

    story.append(
        Spacer(
            1,
            12,
        )
    )

    story.append(
        Paragraph(
            L["offer_text"],
            body_style,
        )
    )

    story.append(
        Spacer(
            1,
            12,
        )
    )

    # --------------------------------------------------------
    # Line items
    # --------------------------------------------------------

    table_data = [
        [
            Paragraph(
                L["description"],
                table_header_style,
            ),
            Paragraph(
                L["quantity"],
                table_header_style,
            ),
            Paragraph(
                L["unit_price"],
                table_header_style,
            ),
            Paragraph(
                L["vat"],
                table_header_style,
            ),
            Paragraph(
                L["amount"],
                table_header_style,
            ),
        ]
    ]

    subtotal = 0.0
    total_tax = 0.0

    for item in quote.get(
        "items",
        [],
    ):
        description = (
            item.get("description")
            or ""
        )

        quantity = float(
            item.get(
                "quantity",
                1,
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

        amount = (
            quantity
            * unit_price
        )

        tax = (
            amount
            * tax_rate
            / 100
        )

        subtotal += amount
        total_tax += tax

        table_data.append(
            [
                Paragraph(
                    safe(description),
                    table_body_style,
                ),
                Paragraph(
                    f"{quantity:g}",
                    table_body_style,
                ),
                Paragraph(
                    f"{money(unit_price)} {safe(currency)}",
                    table_body_style,
                ),
                Paragraph(
                    f"{tax_rate:g}%",
                    table_body_style,
                ),
                Paragraph(
                    f"{money(amount)} {safe(currency)}",
                    table_body_style,
                ),
            ]
        )

    total = (
        subtotal
        + total_tax
    )

    items_table = Table(
        table_data,
        colWidths=[
            76 * mm,
            20 * mm,
            29 * mm,
            20 * mm,
            32 * mm,
        ],
        repeatRows=1,
    )

    items_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#222222"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#DDDDDD"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(items_table)

    story.append(
        Spacer(
            1,
            12,
        )
    )

    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    totals_table = Table(
        [
            [
                "",
                Paragraph(
                    L["subtotal"],
                    body_style,
                ),
                Paragraph(
                    f"{money(subtotal)} {safe(currency)}",
                    body_style,
                ),
            ],
            [
                "",
                Paragraph(
                    L["vat"],
                    body_style,
                ),
                Paragraph(
                    f"{money(total_tax)} {safe(currency)}",
                    body_style,
                ),
            ],
            [
                "",
                Paragraph(
                    L["total"],
                    total_style,
                ),
                Paragraph(
                    f"{money(total)} {safe(currency)}",
                    total_style,
                ),
            ],
        ],
        colWidths=[
            88 * mm,
            44 * mm,
            45 * mm,
    ],
    )

    totals_table.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "LINEABOVE",
                    (1, 2),
                    (-1, 2),
                    1,
                    colors.HexColor("#222222"),
                ),
                (
                    "TOPPADDING",
                    (1, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (1, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(totals_table)

    # --------------------------------------------------------
    # Notes
    # --------------------------------------------------------

    notes = quote.get(
        "notes"
    )

    if notes:
        story.append(
            Spacer(
                1,
                18,
            )
        )

        story.append(
            Paragraph(
                L["notes"],
                section_style,
            )
        )

        story.append(
            Paragraph(
                safe(notes).replace(
                    "\n",
                    "<br/>",
                ),
                body_style,
            )
        )

    # --------------------------------------------------------
    # Company legal information
    # --------------------------------------------------------

    legal_parts = []

    if company_vat:
        legal_parts.append(
            f"{L['vat_id']}: {safe(company_vat)}"
        )

    if company_kvk:
        legal_parts.append(
            f"{L['kvk']}: {safe(company_kvk)}"
        )

    if company_iban:
        legal_parts.append(
            f"IBAN: {safe(company_iban)}"
        )

    if legal_parts:
        story.append(
            Spacer(
                1,
                20,
            )
        )

        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#DDDDDD"),
                spaceBefore=2,
                spaceAfter=7,
            )
        )

        story.append(
            Paragraph(
                " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(
                    legal_parts
                ),
                small_style,
            )
        )

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    doc.build(story)

    return buffer.getvalue()


@router.get("/quotes")
async def list_quotes(
    user: UserDep,
):
    docs = await _r_q().list(
        user.tenant_id,
        limit=500,
    )

    for doc in docs:
        doc["totals"] = _totals(
            doc.get("items", [])
        )

    return docs


@router.post(
    "/quotes",
    status_code=201,
)
async def create_quote(
    body: QuoteIn,
    user: UserDep,
):
    data = body.model_dump()

    if not data.get("number"):
        count = await _r_q().count(
            user.tenant_id
        )

        data["number"] = f"QUO-{count + 1:05d}"

    doc = await _r_q().create(
        user.tenant_id,
        data,
    )

    doc["totals"] = _totals(
        doc.get("items", [])
    )

    return doc


@router.patch("/quotes/{qid}")
async def update_quote(
    qid: str,
    body: QuoteIn,
    user: UserDep,
):
    doc = await _r_q().update(
        user.tenant_id,
        qid,
        body.model_dump(),
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Quote not found",
        )

    doc["totals"] = _totals(
        doc.get("items", [])
    )

    return doc


@router.get("/quotes/{qid}/pdf")
async def quote_pdf(
    qid: str,
    user: UserDep,
):
    db = get_db()

    quote = await db.quotes.find_one(
        {
            "id": qid,
            "tenant_id": user.tenant_id,
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

    tenant = await db.tenants.find_one(
        {
            "id": user.tenant_id,
        },
        {
            "_id": 0,
        },
    ) or {}

    pdf_bytes = _render_quote_pdf(
        quote,
        tenant,
        client,
    )

    filename = (
        f"{quote.get('number') or 'quote'}.pdf"
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{filename}"'
            )
        },
    )


@router.post(
    "/quotes/{qid}/send",
)
async def send_quote(
    qid: str,
    user: UserDep,
):
    db = get_db()

    # --------------------------------------------------------
    # Load quote
    # --------------------------------------------------------

    quote = await db.quotes.find_one(
        {
            "id": qid,
            "tenant_id": user.tenant_id,
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

    # --------------------------------------------------------
    # Load client
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
        or ""
    )

    if not client_email:
        raise HTTPException(
            status_code=400,
            detail="The selected client does not have an email address.",
        )

    # --------------------------------------------------------
    # Load tenant/company
    # --------------------------------------------------------

    tenant = await db.tenants.find_one(
        {
            "id": user.tenant_id,
        },
        {
            "_id": 0,
        },
    ) or {}

    company_name = (
        tenant.get("name")
        or "NED Tech CRM"
    )

    company_email = (
        tenant.get("email")
        or tenant.get("contact_email")
        or None
    )

    quote_number = (
        quote.get("number")
        or qid
    )

    language = _quote_language(
        tenant
    )

    # --------------------------------------------------------
    # Email translations
    # --------------------------------------------------------

    email_translations = {
        "de": {
            "subject": f"Angebot {quote_number} – {company_name}",
            "title": "Ihr Angebot",
            "text": (
                "vielen Dank für Ihre Anfrage. "
                "im Anhang finden Sie unser Angebot."
            ),
            "regards": "Mit freundlichen Grüßen",
        },
        "nl": {
            "subject": f"Offerte {quote_number} – {company_name}",
            "title": "Uw offerte",
            "text": (
                "bedankt voor uw aanvraag. "
                "In de bijlage vindt u onze offerte."
            ),
            "regards": "Met vriendelijke groet",
        },
        "en": {
            "subject": f"Quotation {quote_number} – {company_name}",
            "title": "Your quotation",
            "text": (
                "thank you for your inquiry. "
                "Please find our quotation attached."
            ),
            "regards": "Kind regards",
        },
    }

    E = email_translations[
        language
    ]

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        padding:0;
        background:#f5f5f5;
        font-family:Arial,Helvetica,sans-serif;
        color:#222;
    ">
        <div style="
            max-width:640px;
            margin:30px auto;
            background:#ffffff;
            padding:40px;
            border:1px solid #e5e5e5;
        ">
            <h2 style="
                margin:0 0 20px;
                font-size:24px;
            ">
                {E["title"]}
            </h2>

            <p>
                {E["text"]}
            </p>

            <p>
                <strong>
                    {quote_number}
                </strong>
            </p>

            <p style="
                margin-top:30px;
            ">
                {E["regards"]}
            </p>

            <p style="
                margin:4px 0 0;
                font-weight:bold;
            ">
                {company_name}
            </p>
        </div>
    </body>
    </html>
    """

    # --------------------------------------------------------
    # Generate PDF
    # --------------------------------------------------------

    pdf_bytes = _render_quote_pdf(
        quote,
        tenant,
        client,
    )

    filename = (
        f"{quote_number}.pdf"
    )

    # --------------------------------------------------------
    # Send
    # --------------------------------------------------------

    result = await send_html_email(
        to=client_email,
        subject=E["subject"],
        html=html,
        reply_to=company_email,
        attachments=[
            {
                "filename": filename,
                "content": pdf_bytes,
                "content_type": "application/pdf",
            }
        ],
    )

    if not result.get("sent"):
        reason = result.get(
            "reason",
            "email_send_failed",
        )

        raise HTTPException(
            status_code=502,
            detail=f"Could not send email: {reason}",
        )

    # --------------------------------------------------------
    # Mark quote as sent
    # --------------------------------------------------------

    sent_at = datetime.now(
        timezone.utc
    ).isoformat()

    await db.quotes.update_one(
        {
            "id": qid,
            "tenant_id": user.tenant_id,
        },
        {
            "$set": {
                "status": "sent",
                "sent_to": client_email,
                "sent_at": sent_at,
            }
        },
    )

    return {
        "sent": True,
        "quote_id": qid,
        "quote_number": quote_number,
        "email": client_email,
        "sent_at": sent_at,
        "message_id": result.get("id"),
    }


@router.delete(
    "/quotes/{qid}",
    status_code=204,
)
async def delete_quote(
    qid: str,
    user: UserDep,
):
    await _r_q().delete(
        user.tenant_id,
        qid,
    )

    return None


# ============================================================
# EXPENSES
# ============================================================


@router.get("/expenses")
async def list_expenses(
    user: UserDep,
):
    return await _r_e().list(
        user.tenant_id,
        limit=500,
    )


@router.post(
    "/expenses",
    status_code=201,
)
async def create_expense(
    body: ExpenseIn,
    user: UserDep,
):
    return await _r_e().create(
        user.tenant_id,
        body.model_dump(),
    )


@router.patch("/expenses/{eid}")
async def update_expense(
    eid: str,
    body: ExpenseIn,
    user: UserDep,
):
    doc = await _r_e().update(
        user.tenant_id,
        eid,
        body.model_dump(),
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    return doc


@router.delete(
    "/expenses/{eid}",
    status_code=204,
)
async def delete_expense(
    eid: str,
    user: UserDep,
):
    await _r_e().delete(
        user.tenant_id,
        eid,
    )

    return None


# ============================================================
# REPORTS
# ============================================================


@router.get("/reports/summary")
async def finance_summary(
    user: UserDep,
):
    invoices = await _r_inv().list(
        user.tenant_id,
        limit=5000,
    )

    expenses = await _r_e().list(
        user.tenant_id,
        limit=5000,
    )

    revenue = sum(
        _totals(
            invoice.get("items", [])
        )["total"]
        for invoice in invoices
        if invoice.get("status") == "paid"
    )

    outstanding = sum(
        _totals(
            invoice.get("items", [])
        )["total"]
        for invoice in invoices
        if invoice.get("status")
        in ("sent", "overdue")
    )

    total_expenses = sum(
        expense.get("amount", 0)
        * (
            1
            + expense.get("tax_rate", 0)
            / 100
        )
        for expense in expenses
    )

    return {
        "revenue": round(
            revenue,
            2,
        ),
        "outstanding": round(
            outstanding,
            2,
        ),
        "expenses": round(
            total_expenses,
            2,
        ),
        "profit": round(
            revenue - total_expenses,
            2,
        ),
        "invoice_count": len(invoices),
        "expense_count": len(expenses),
    }