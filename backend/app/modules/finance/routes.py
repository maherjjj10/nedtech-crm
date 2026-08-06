"""Finance: quotes, invoices, expenses. Simple PDF export via reportlab."""
from typing import Optional
from io import BytesIO
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository

router = APIRouter(tags=["Finance"], dependencies=[Depends(module_gate("finance"))])


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
        _invoices = BaseRepository(get_db(), InvoiceIn, "invoices")
    return _invoices


def _r_q() -> BaseRepository:
    global _quotes
    if _quotes is None:
        _quotes = BaseRepository(get_db(), QuoteIn, "quotes")
    return _quotes


def _r_e() -> BaseRepository:
    global _expenses
    if _expenses is None:
        _expenses = BaseRepository(get_db(), ExpenseIn, "expenses")
    return _expenses


def _totals(items: list[dict]) -> dict:
    subtotal = sum((i.get("quantity", 0) * i.get("unit_price", 0)) for i in items)
    tax = sum((i.get("quantity", 0) * i.get("unit_price", 0)) * (i.get("tax_rate", 0) / 100) for i in items)
    return {"subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": round(subtotal + tax, 2)}


# ------- Invoices -------
@router.get("/invoices")
async def list_invoices(user: UserDep):
    docs = await _r_inv().list(user.tenant_id, limit=500)
    for d in docs:
        d["totals"] = _totals(d.get("items", []))
    return docs


@router.post("/invoices", status_code=201)
async def create_invoice(body: InvoiceIn, user: UserDep):
    data = body.model_dump()
    if not data.get("number"):
        count = await _r_inv().count(user.tenant_id)
        data["number"] = f"INV-{count + 1:05d}"
    doc = await _r_inv().create(user.tenant_id, data)
    doc["totals"] = _totals(doc.get("items", []))
    return doc


@router.get("/invoices/{iid}")
async def get_invoice(iid: str, user: UserDep):
    d = await _r_inv().get(user.tenant_id, iid)
    if not d: raise HTTPException(404, "Invoice not found")
    d["totals"] = _totals(d.get("items", []))
    return d


@router.patch("/invoices/{iid}")
async def update_invoice(iid: str, body: InvoiceIn, user: UserDep):
    d = await _r_inv().update(user.tenant_id, iid, body.model_dump())
    if not d: raise HTTPException(404, "Invoice not found")
    d["totals"] = _totals(d.get("items", []))
    return d


@router.delete("/invoices/{iid}", status_code=204)
async def delete_invoice(iid: str, user: UserDep):
    await _r_inv().delete(user.tenant_id, iid)


@router.get("/invoices/{iid}/pdf")
async def invoice_pdf(iid: str, user: UserDep):
    inv = await _r_inv().get(user.tenant_id, iid)
    if not inv: raise HTTPException(404, "Invoice not found")
    tenant = await get_db().tenants.find_one({"id": user.tenant_id}, {"_id": 0}) or {}
    pdf = _render_invoice_pdf(inv, tenant)
    return StreamingResponse(
        BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{inv.get("number", "invoice")}.pdf"'},
    )


def _render_invoice_pdf(inv: dict, tenant: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=inv.get("number", "Invoice"))
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{tenant.get('name', 'Company')}</b>", styles["Title"]))
    story.append(Paragraph(f"Invoice {inv.get('number', '')}", styles["Heading2"]))
    story.append(Paragraph(f"Bill to: {inv.get('client_name', '')}", styles["Normal"]))
    story.append(Paragraph(f"Issue: {inv.get('issue_date', '')} &nbsp;&nbsp; Due: {inv.get('due_date', '')}", styles["Normal"]))
    story.append(Spacer(1, 12))
    rows = [["Description", "Qty", "Unit", "Tax %", "Amount"]]
    for it in inv.get("items", []):
        amt = it.get("quantity", 0) * it.get("unit_price", 0)
        rows.append([it.get("description", ""), it.get("quantity"), f"{it.get('unit_price'):.2f}",
                     f"{it.get('tax_rate', 0):.1f}", f"{amt:.2f}"])
    t = Table(rows, hAlign="LEFT", colWidths=[220, 50, 60, 50, 70])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    tot = _totals(inv.get("items", []))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Subtotal: {inv.get('currency','USD')} {tot['subtotal']:.2f}", styles["Normal"]))
    story.append(Paragraph(f"Tax: {inv.get('currency','USD')} {tot['tax']:.2f}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total: {inv.get('currency','USD')} {tot['total']:.2f}</b>", styles["Heading3"]))
    if inv.get("notes"):
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Notes: {inv['notes']}", styles["Italic"]))
    doc.build(story)
    return buf.getvalue()


# ------- Quotes -------
@router.get("/quotes")
async def list_quotes(user: UserDep):
    docs = await _r_q().list(user.tenant_id, limit=500)
    for d in docs: d["totals"] = _totals(d.get("items", []))
    return docs


@router.post("/quotes", status_code=201)
async def create_quote(body: QuoteIn, user: UserDep):
    data = body.model_dump()
    if not data.get("number"):
        count = await _r_q().count(user.tenant_id)
        data["number"] = f"QUO-{count + 1:05d}"
    d = await _r_q().create(user.tenant_id, data)
    d["totals"] = _totals(d.get("items", []))
    return d


@router.patch("/quotes/{qid}")
async def update_quote(qid: str, body: QuoteIn, user: UserDep):
    d = await _r_q().update(user.tenant_id, qid, body.model_dump())
    if not d: raise HTTPException(404, "Quote not found")
    d["totals"] = _totals(d.get("items", []))
    return d


@router.delete("/quotes/{qid}", status_code=204)
async def delete_quote(qid: str, user: UserDep):
    await _r_q().delete(user.tenant_id, qid)


# ------- Expenses -------
@router.get("/expenses")
async def list_expenses(user: UserDep):
    return await _r_e().list(user.tenant_id, limit=500)


@router.post("/expenses", status_code=201)
async def create_expense(body: ExpenseIn, user: UserDep):
    return await _r_e().create(user.tenant_id, body.model_dump())


@router.patch("/expenses/{eid}")
async def update_expense(eid: str, body: ExpenseIn, user: UserDep):
    d = await _r_e().update(user.tenant_id, eid, body.model_dump())
    if not d: raise HTTPException(404, "Expense not found")
    return d


@router.delete("/expenses/{eid}", status_code=204)
async def delete_expense(eid: str, user: UserDep):
    await _r_e().delete(user.tenant_id, eid)


# ------- Reports -------
@router.get("/reports/summary")
async def finance_summary(user: UserDep):
    invoices = await _r_inv().list(user.tenant_id, limit=5000)
    expenses = await _r_e().list(user.tenant_id, limit=5000)
    revenue = sum(_totals(inv.get("items", []))["total"] for inv in invoices if inv.get("status") == "paid")
    outstanding = sum(_totals(inv.get("items", []))["total"] for inv in invoices if inv.get("status") in ("sent", "overdue"))
    total_expenses = sum(e.get("amount", 0) * (1 + e.get("tax_rate", 0) / 100) for e in expenses)
    return {
        "revenue": round(revenue, 2),
        "outstanding": round(outstanding, 2),
        "expenses": round(total_expenses, 2),
        "profit": round(revenue - total_expenses, 2),
        "invoice_count": len(invoices),
        "expense_count": len(expenses),
    }
