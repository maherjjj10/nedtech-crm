"""Finance: quotes, invoices, expenses. Simple PDF export via reportlab."""

from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository


router = APIRouter(
    tags=["Finance"],
    dependencies=[
        Depends(module_gate("finance")),
        Depends(require_permission("finance")),
    ],
)


class LineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float = 0
    tax_rate: float = 0  # percent


class InvoiceIn(BaseModel):
    number: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "USD"
    items: list[LineItem] = Field(default_factory=list)
    notes: Optional[str] = None
    status: str = "draft"  # draft | sent | paid | overdue | cancelled


class QuoteIn(InvoiceIn):
    status: str = "draft"  # draft | sent | accepted | rejected


class ExpenseIn(BaseModel):
    date: Optional[str] = None
    category: str = "general"
    vendor: Optional[str] = None
    amount: float = 0
    currency: str = "USD"
    tax_rate: float = 0
    description: Optional[str] = None
    receipt_url: Optional[str] = None


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


# ─────────────────────────────────────────────
# Invoices
# ─────────────────────────────────────────────


@router.get("/invoices")
async def list_invoices(user: UserDep):
    docs = await _r_inv().list(
        user.tenant_id,
        limit=500,
    )

    for doc in docs:
        doc["totals"] = _totals(
            doc.get("items", [])
        )

    return docs


@router.post("/invoices", status_code=201)
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

    return doc


@router.delete("/invoices/{iid}", status_code=204)
async def delete_invoice(
    iid: str,
    user: UserDep,
):
    await _r_inv().delete(
        user.tenant_id,
        iid,
    )

    return None


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

    # Use the requested language when supplied; otherwise inherit
    # the tenant/workspace language. Never force English by default.
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
                f'attachment; '
                f'filename="{invoice.get("number", "invoice")}.pdf"'
            )
        },
    )


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

    # ============================================================
    # PAGE
    # ============================================================

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

    # ============================================================
    # COLORS
    # ============================================================

    DARK = colors.HexColor("#171717")
    TEXT = colors.HexColor("#242424")
    MUTED = colors.HexColor("#6B7280")
    BORDER = colors.HexColor("#E5E7EB")
    LIGHT = colors.HexColor("#F7F7F7")
    WHITE = colors.white

    # ============================================================
    # STYLES
    # ============================================================

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

    # ============================================================
    # HELPERS
    # ============================================================

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

    # ============================================================
    # PDF LANGUAGE
    # ============================================================
    locale = str(lang or tenant.get("locale") or tenant.get("language") or "en")
    locale = locale.lower().replace("_", "-").split("-")[0]
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

    # ============================================================
    # COMPANY
    # ============================================================

    company_name = tenant.get("name") or "Company"
    company_address = tenant.get("address") or ""
    company_phone = tenant.get("phone") or ""
    company_website = tenant.get("website") or ""
    company_iban = tenant.get("iban") or ""
    company_kvk = tenant.get("kvk_number") or ""
    company_vat = tenant.get("vat_number") or ""

    # ============================================================
    # INVOICE
    # ============================================================

    invoice_number = invoice.get("number") or ""
    issue_date = invoice.get("issue_date") or ""
    due_date = invoice.get("due_date") or ""

    currency = (
        invoice.get("currency")
        or tenant.get("currency")
        or "EUR"
    )

    # ============================================================
    # CLIENT
    # ============================================================

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

    # ============================================================
    # STORY
    # ============================================================

    story = []

    # ============================================================
    # HEADER
    # ============================================================

    company_block = [
        Paragraph(
            safe(company_name),
            company_style,
        )
    ]

    # Full company information in the invoice header
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
            f"<b>{L['invoice_no']}</b>&nbsp;&nbsp;{safe(invoice_number)}",
            meta_value,
        ),
        Paragraph(
            f"<b>{L['issue_date']}</b>&nbsp;&nbsp;{safe(issue_date)}",
            meta_value,
        ),
        Paragraph(
            f"<b>{L['due_date']}</b>&nbsp;&nbsp;{safe(due_date)}",
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
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
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

    # ============================================================
    # BILL TO
    # ============================================================

    bill_to = [
        Paragraph(L["bill_to"], section),
        Spacer(1, 4),
    ]

    if client_company:
        bill_to.append(
            Paragraph(f"<b>{safe(client_company)}</b>", body)
        )

    if client_name:
        bill_to.append(
            Paragraph(safe(client_name), body)
        )

    if client_contact:
        bill_to.append(
            Paragraph(safe(client_contact), small)
        )

    if client_address:
        bill_to.append(
            Paragraph(safe(client_address), small)
        )

    if client_email:
        bill_to.append(
            Paragraph(safe(client_email), small)
        )

    if client_phone:
        bill_to.append(
            Paragraph(safe(client_phone), small)
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
        colWidths=[177 * mm],
    )

    bill_to_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    story.append(bill_to_table)
    story.append(Spacer(1, 18))

    # ============================================================
    # ITEMS
    # ============================================================

    item_rows = [
        [
            Paragraph(L["description"], table_header),
            Paragraph(L["qty"], table_header_right),
            Paragraph(L["unit_price"], table_header_right),
            Paragraph(L["vat"], table_header_right),
            Paragraph(L["amount"], table_header_right),
        ]
    ]

    for item in invoice.get("items", []):
        quantity = item.get("quantity", 0) or 0
        unit_price = item.get("unit_price", 0) or 0
        tax_rate = item.get("tax_rate", 0) or 0

        try:
            amount = float(quantity) * float(unit_price)
        except (TypeError, ValueError):
            amount = 0

        item_rows.append(
            [
                Paragraph(
                    safe(item.get("description", "")),
                    body,
                ),
                Paragraph(
                    safe(quantity),
                    body_right,
                ),
                Paragraph(
                    f"{safe(currency)} {money(unit_price)}",
                    body_right,
                ),
                Paragraph(
                    f"{float(tax_rate):.1f}%",
                    body_right,
                ),
                Paragraph(
                    f"{safe(currency)} {money(amount)}",
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
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, DARK),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )

    story.append(items_table)
    story.append(Spacer(1, 16))

    # ============================================================
    # TOTALS
    # ============================================================

    totals = _totals(
        invoice.get("items", [])
    )

    totals_rows = [
        [
            "",
            Paragraph(L["subtotal"], body),
            Paragraph(
                f"{safe(currency)} {money(totals['subtotal'])}",
                body_right,
            ),
        ],
        [
            "",
            Paragraph(L["vat"], body),
            Paragraph(
                f"{safe(currency)} {money(totals['tax'])}",
                body_right,
            ),
        ],
        [
            "",
            Paragraph(f"<b>{L['total']}</b>", total_label),
            Paragraph(
                f"<b>{safe(currency)} {money(totals['total'])}</b>",
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
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, 1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 1), 4),
                ("TOPPADDING", (0, 2), (-1, 2), 8),
                ("BOTTOMPADDING", (0, 2), (-1, 2), 8),
                ("LINEABOVE", (1, 2), (-1, 2), 1.2, DARK),
            ]
        )
    )

    story.append(totals_table)

    # ============================================================
    # PAYMENT INFORMATION
    # ============================================================

    if company_iban:
        story.append(Spacer(1, 18))

        payment_block = [
            Paragraph(
                L["payment"],
                section,
            ),
            Spacer(1, 5),
        ]

        # Show the company identity again in the payment section
        if company_name:
            payment_block.append(
                Paragraph(
                    f"<b>{L['account_holder']}:</b> {safe(company_name)}",
                    body,
                )
            )

        if company_address:
            payment_block.append(
                Paragraph(
                    f"<b>{L['address']}:</b> {safe(company_address)}",
                    body,
                )
            )

        if company_iban:
            payment_block.append(
                Paragraph(
                    f"<b>{L['iban']}:</b> {safe(company_iban)}",
                    body,
                )
            )

        if company_phone:
            payment_block.append(
                Paragraph(
                    f"<b>{L['tel']}:</b> {safe(company_phone)}",
                    body,
                )
            )

        if company_website:
            payment_block.append(
                Paragraph(
                    f"<b>{L['website']}:</b> {safe(company_website)}",
                    body,
                )
            )

        payment_table = Table(
            [[payment_block]],
            colWidths=[177 * mm],
        )

        payment_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )

        story.append(payment_table)

    # ============================================================
    # NOTES
    # ============================================================

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

    # ============================================================
    # FOOTER
    # ============================================================

    def draw_footer(canvas, doc):
        canvas.saveState()

        # Keep the footer compact and readable on every page.
        footer_y = 10 * mm

        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)

        canvas.line(
            doc.leftMargin,
            footer_y + 18,
            PAGE_WIDTH - doc.rightMargin,
            footer_y + 18,
        )

        # Company name
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(TEXT)
        canvas.drawString(
            doc.leftMargin,
            footer_y + 8,
            str(company_name),
        )

        # Left-side company contact details
        canvas.setFont("Helvetica", 6.7)
        canvas.setFillColor(MUTED)

        footer_left = []

        if company_address:
            footer_left.append(str(company_address))

        if company_phone:
            footer_left.append(f"{L['tel']}: {company_phone}")

        if company_website:
            footer_left.append(str(company_website))

        footer_line = "  |  ".join(footer_left)

        if footer_line:
            canvas.drawString(
                doc.leftMargin,
                footer_y - 2,
                footer_line,
            )

        # Right-side legal / banking details
        footer_right = []

        if company_iban:
            footer_right.append(f"IBAN: {company_iban}")

        if company_kvk:
            footer_right.append(
                f"{L['kvk']}: {company_kvk}"
            )

        if company_vat:
            footer_right.append(
                f"{L['vat_id']}: {company_vat}"
            )

        legal_line = "  |  ".join(footer_right)

        if legal_line:
            canvas.drawRightString(
                PAGE_WIDTH - doc.rightMargin,
                footer_y + 8,
                legal_line,
            )

        # Page number
        canvas.setFont("Helvetica", 6.7)
        canvas.setFillColor(MUTED)

        canvas.drawRightString(
            PAGE_WIDTH - doc.rightMargin,
            footer_y - 12,
            f"{L['page']} {canvas.getPageNumber()}",
        )

        canvas.restoreState()

    # ============================================================
    # BUILD
    # ============================================================

    doc.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    return buffer.getvalue()


# ─────────────────────────────────────────────
# Quotes
# ─────────────────────────────────────────────


@router.get("/quotes")
async def list_quotes(user: UserDep):
    docs = await _r_q().list(
        user.tenant_id,
        limit=500,
    )

    for doc in docs:
        doc["totals"] = _totals(
            doc.get("items", [])
        )

    return docs


@router.post("/quotes", status_code=201)
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


@router.delete("/quotes/{qid}", status_code=204)
async def delete_quote(
    qid: str,
    user: UserDep,
):
    await _r_q().delete(
        user.tenant_id,
        qid,
    )

    return None


# ─────────────────────────────────────────────
# Expenses
# ─────────────────────────────────────────────


@router.get("/expenses")
async def list_expenses(user: UserDep):
    return await _r_e().list(
        user.tenant_id,
        limit=500,
    )


@router.post("/expenses", status_code=201)
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


@router.delete("/expenses/{eid}", status_code=204)
async def delete_expense(
    eid: str,
    user: UserDep,
):
    await _r_e().delete(
        user.tenant_id,
        eid,
    )

    return None


# ─────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────


@router.get("/reports/summary")
async def finance_summary(user: UserDep):
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
        "revenue": round(revenue, 2),
        "outstanding": round(outstanding, 2),
        "expenses": round(total_expenses, 2),
        "profit": round(
            revenue - total_expenses,
            2,
        ),
        "invoice_count": len(invoices),
        "expense_count": len(expenses),
    }