"""Quote Approval → Invoice Flow.

Public share link so clients can view, accept or reject a quote without an
account. On accept, the quote can be converted to an invoice with one call,
and optionally spin up a project scaffold.
"""
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import new_id, utcnow_iso

router = APIRouter(prefix="/quotes", tags=["Quote Flow"],
                   dependencies=[Depends(module_gate("finance"))])
public_router = APIRouter(prefix="/public/quotes", tags=["Public Quote"])


class DecisionIn(BaseModel):
    decision: str          # "accepted" | "rejected"
    comment: Optional[str] = None
    signer_name: Optional[str] = None


class ConvertRequest(BaseModel):
    create_project: bool = False


def _totals(items: list[dict]) -> dict:
    subtotal = sum(i.get("quantity", 0) * i.get("unit_price", 0) for i in items)
    tax = sum(i.get("quantity", 0) * i.get("unit_price", 0) * (i.get("tax_rate", 0) / 100)
              for i in items)
    return {"subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": round(subtotal + tax, 2)}


@router.post("/{qid}/share")
async def share_quote(qid: str, user: UserDep):
    db = get_db()
    q = await db.quotes.find_one({"tenant_id": user.tenant_id, "id": qid})
    if not q:
        raise HTTPException(404, "Quote not found")
    if q.get("status") in ("accepted", "rejected", "converted"):
        raise HTTPException(409, f"Cannot share a quote that is already {q['status']}")
    token = q.get("share_token") or secrets.token_urlsafe(24)
    await db.quotes.update_one(
        {"tenant_id": user.tenant_id, "id": qid},
        {"$set": {"share_token": token, "status": "sent", "updated_at": utcnow_iso()}},
    )
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return {"share_token": token, "public_url": f"{base}/public/quote/{token}"}


@router.get("/{qid}")
async def get_quote(qid: str, user: UserDep):
    db = get_db()
    q = await db.quotes.find_one({"tenant_id": user.tenant_id, "id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Quote not found")
    q["totals"] = _totals(q.get("items", []))
    return q


@public_router.get("/{token}")
async def public_get_quote(token: str):
    db = get_db()
    q = await db.quotes.find_one({"share_token": token}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Quote not found")
    q["totals"] = _totals(q.get("items", []))
    tenant = await db.tenants.find_one({"id": q["tenant_id"]}, {"_id": 0, "modules": 0}) or {}
    return {"quote": q,
            "tenant": {"name": tenant.get("name"), "logo_url": tenant.get("logo_url"),
                       "address": tenant.get("address"), "website": tenant.get("website"),
                       "currency": tenant.get("currency")}}


@public_router.post("/{token}/decision")
async def public_decide(token: str, body: DecisionIn):
    if body.decision not in ("accepted", "rejected"):
        raise HTTPException(400, "decision must be 'accepted' or 'rejected'")
    db = get_db()
    q = await db.quotes.find_one({"share_token": token})
    if not q:
        raise HTTPException(404, "Quote not found")
    if q.get("status") in ("accepted", "rejected", "converted"):
        raise HTTPException(409, f"Quote already {q['status']}")
    await db.quotes.update_one(
        {"id": q["id"]},
        {"$set": {"status": body.decision,
                  "decision_comment": body.comment,
                  "signer_name": body.signer_name,
                  "decided_at": utcnow_iso(),
                  "updated_at": utcnow_iso()}},
    )
    await db.activities.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": q["tenant_id"],
        "type": f"quote_{body.decision}", "entity_id": q["id"],
        "message": f"Quote {q.get('number','')} {body.decision}"
                   + (f" by {body.signer_name}" if body.signer_name else ""),
        "actor": body.signer_name or "client", "created_at": utcnow_iso(),
    })
    return {"ok": True, "status": body.decision}


@router.post("/{qid}/convert", status_code=201)
async def convert_quote_to_invoice(qid: str, body: ConvertRequest, user: UserDep):
    db = get_db()
    q = await db.quotes.find_one({"tenant_id": user.tenant_id, "id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(404, "Quote not found")
    if q.get("converted_invoice_id") or q.get("status") == "converted":
        raise HTTPException(409, "Already converted")
    if q.get("status") != "accepted":
        raise HTTPException(400, "Only accepted quotes can be converted")

    inv_count = await db.invoices.count_documents({"tenant_id": user.tenant_id})
    inv_id = new_id()
    invoice = {
        "_id": inv_id, "id": inv_id, "tenant_id": user.tenant_id,
        "number": f"INV-{inv_count + 1:05d}",
        "client_id": q.get("client_id"), "client_name": q.get("client_name"),
        "issue_date": utcnow_iso()[:10], "due_date": None,
        "currency": q.get("currency", "USD"),
        "items": q.get("items", []),
        "status": "draft", "notes": q.get("notes"),
        "source_quote_id": q["id"],
        "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
    }
    await db.invoices.insert_one(invoice)

    project_id = None
    if body.create_project:
        project_id = new_id()
        await db.projects.insert_one({
            "_id": project_id, "id": project_id, "tenant_id": user.tenant_id,
            "name": f"{q.get('client_name','Client')} — {q.get('number','Project')}",
            "client_id": q.get("client_id"), "status": "active", "color": "#171717",
            "description": q.get("notes"),
            "source_quote_id": q["id"],
            "created_at": utcnow_iso(), "updated_at": utcnow_iso(),
        })

    await db.quotes.update_one(
        {"tenant_id": user.tenant_id, "id": qid},
        {"$set": {"converted_invoice_id": inv_id, "converted_project_id": project_id,
                  "status": "converted", "updated_at": utcnow_iso()}},
    )
    return {"invoice_id": inv_id, "project_id": project_id}
