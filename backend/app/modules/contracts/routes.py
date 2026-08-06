"""Contracts V2 — Enterprise contract management.

Features:
  - CRM-integrated client picker (snapshot: company, contact_person, email,
    phone, address, vat_number captured at creation)
  - Template library (seeded 8 industry templates + unlimited user templates)
  - Dynamic variables ({{client_name}}, {{today_date}}, {{contract_amount}}, ...)
    resolved on send / pdf / public view
  - Rich HTML body (TipTap)
  - PDF with company logo, verification ID, QR code, page numbers, sig block
  - Public share link for view / sign / reject / comment (no CRM auth)
  - Signature methods: typed | drawn (mouse/touch canvas → base64 PNG)
  - Full status machine + audit trail
  - Version history (full snapshots)

Contract statuses: draft | pending_review | sent | viewed | signed | completed | expired | cancelled
"""
import os
import re
import base64
import secrets
from io import BytesIO
from datetime import datetime, timezone, date
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository, new_id, utcnow_iso

router = APIRouter(prefix="/contracts", tags=["Contracts"],
                   dependencies=[Depends(module_gate("finance"))])
public_router = APIRouter(prefix="/public/contracts", tags=["Public Contract"])


# ---------------------------- Models -----------------------------------------
class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: Optional[str] = None
    body_html: str
    is_system: bool = False


class ContractIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    client_id: Optional[str] = None
    template_id: Optional[str] = None
    body_html: str
    contract_amount: Optional[float] = None
    currency: Optional[str] = "USD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    expires_at: Optional[str] = None   # signing deadline
    invoice_number: Optional[str] = None
    notes: Optional[str] = None


class SignIn(BaseModel):
    signer_name: str = Field(min_length=1, max_length=120)
    signer_email: Optional[str] = None
    signature_type: str = "typed"                        # typed | drawn
    signature_data: Optional[str] = None                 # base64 PNG for drawn
    consent: bool = True


class RejectIn(BaseModel):
    signer_name: Optional[str] = None
    reason: str = Field(min_length=1, max_length=2000)


class CommentIn(BaseModel):
    author: str
    body: str


# ---------------------------- Repos ------------------------------------------
_templates: BaseRepository | None = None
_contracts: BaseRepository | None = None


def _tpl_repo() -> BaseRepository:
    global _templates
    if _templates is None:
        _templates = BaseRepository(get_db(), TemplateIn, "contract_templates")
    return _templates


def _ct_repo() -> BaseRepository:
    global _contracts
    if _contracts is None:
        _contracts = BaseRepository(get_db(), ContractIn, "contracts")
    return _contracts


# ---------------------------- Helpers ----------------------------------------
def _short_id() -> str:
    """Human-readable verification id: NED-C-XXXXXX."""
    return f"NED-C-{secrets.token_hex(3).upper()}"


def _is_expired(c: dict) -> bool:
    if c.get("status") in ("signed", "completed") or not c.get("expires_at"):
        return False
    try:
        return date.today().isoformat() > c["expires_at"]
    except Exception:
        return False


def _now() -> str:
    return utcnow_iso()


def _client_snapshot(client: dict) -> dict:
    """Snapshot of client at contract-creation time. Immutable per contract."""
    return {
        "client_id": client.get("id"),
        "client_name": client.get("name"),
        "company": client.get("company"),
        "contact_person": client.get("contact_person") or client.get("name"),
        "email": client.get("email"),
        "phone": client.get("phone"),
        "address": client.get("address"),
        "vat_number": client.get("vat_number"),
        "website": client.get("website"),
    }


def _build_variables(contract: dict, tenant: dict) -> dict:
    snap = contract.get("client_snapshot") or {}
    today = date.today().isoformat()
    return {
        "client_name": snap.get("client_name") or "",
        "company_name": snap.get("company") or snap.get("client_name") or "",
        "contact_person": snap.get("contact_person") or "",
        "email": snap.get("email") or "",
        "phone": snap.get("phone") or "",
        "address": snap.get("address") or "",
        "vat_number": snap.get("vat_number") or "",
        "today_date": today,
        "start_date": contract.get("start_date") or "",
        "end_date": contract.get("end_date") or "",
        "contract_amount": (
            f"{contract.get('currency','USD')} {contract.get('contract_amount'):,.2f}"
            if contract.get("contract_amount") is not None else ""
        ),
        "invoice_number": contract.get("invoice_number") or "",
        "company_name_ours": tenant.get("name") or "",
        "company_logo": tenant.get("logo_url") or "",
        "company_signature": tenant.get("name") or "",
    }


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _resolve_variables(text: str, vars_: dict) -> str:
    if not text:
        return ""
    return _VAR_RE.sub(lambda m: str(vars_.get(m.group(1), m.group(0))), text)


def _push_version(db, contract: dict, actor: str, note: str = ""):
    """Append a snapshot of current contract to versions collection."""
    vid = new_id()
    doc = {
        "_id": vid, "id": vid,
        "tenant_id": contract["tenant_id"],
        "contract_id": contract["id"],
        "created_at": _now(),
        "actor": actor,
        "note": note,
        "snapshot": {
            "title": contract.get("title"),
            "body_html": contract.get("body_html"),
            "status": contract.get("status"),
            "contract_amount": contract.get("contract_amount"),
            "currency": contract.get("currency"),
            "start_date": contract.get("start_date"),
            "end_date": contract.get("end_date"),
            "expires_at": contract.get("expires_at"),
            "client_snapshot": contract.get("client_snapshot"),
        },
    }
    return db.contract_versions.insert_one(doc)


async def _audit(db, contract: dict, event: str, actor: str, meta: dict | None = None):
    ev_id = new_id()
    await db.contract_audit.insert_one({
        "_id": ev_id, "id": ev_id,
        "tenant_id": contract["tenant_id"],
        "contract_id": contract["id"],
        "event": event,
        "actor": actor,
        "meta": meta or {},
        "created_at": _now(),
    })


# ---------------------------- Templates --------------------------------------
@router.get("/templates")
async def list_templates(user: UserDep):
    docs = await get_db().contract_templates.find(
        {"$or": [{"tenant_id": user.tenant_id}, {"tenant_id": None, "is_system": True}]},
        {"_id": 0},
    ).sort([("is_system", -1), ("name", 1)]).to_list(length=500)
    return docs


@router.post("/templates", status_code=201)
async def create_template(body: TemplateIn, user: UserDep):
    data = body.model_dump()
    data["is_system"] = False
    return await _tpl_repo().create(user.tenant_id, data)


@router.patch("/templates/{tid}")
async def update_template(tid: str, body: TemplateIn, user: UserDep):
    t = await _tpl_repo().update(user.tenant_id, tid, body.model_dump())
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.delete("/templates/{tid}", status_code=204)
async def delete_template(tid: str, user: UserDep):
    tpl = await get_db().contract_templates.find_one({"id": tid})
    if tpl and tpl.get("is_system"):
        raise HTTPException(400, "System templates cannot be deleted")
    await _tpl_repo().delete(user.tenant_id, tid)


# ---------------------------- Contracts (internal) ---------------------------
@router.get("")
async def list_contracts(
    user: UserDep,
    client_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
):
    filters: dict = {}
    if client_id:
        filters["client_id"] = client_id
    if status:
        filters["status"] = status
    if q:
        filters["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"client_snapshot.client_name": {"$regex": q, "$options": "i"}},
            {"client_snapshot.company": {"$regex": q, "$options": "i"}},
        ]
    contracts = await _ct_repo().list(user.tenant_id, filters, limit=500)
    for c in contracts:
        if _is_expired(c) and c.get("status") not in ("expired", "signed", "completed"):
            c["status"] = "expired"
    return contracts


@router.post("", status_code=201)
async def create_contract(body: ContractIn, user: UserDep):
    db = get_db()
    data = body.model_dump()
    if data.get("client_id"):
        client = await db.clients.find_one({"tenant_id": user.tenant_id, "id": data["client_id"]}, {"_id": 0})
        if not client:
            raise HTTPException(400, "Client not found")
        data["client_snapshot"] = _client_snapshot(client)
    else:
        data["client_snapshot"] = None
    data["status"] = "draft"
    data["verification_id"] = _short_id()
    data["comments"] = []
    data["viewed_at"] = None
    data["version"] = 1
    created = await _ct_repo().create(user.tenant_id, data)
    await _push_version(db, created, user.email, "created")
    await _audit(db, created, "created", user.email)
    await db.activities.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": user.tenant_id,
        "type": "contract_created",
        "entity_id": data.get("client_id") or created["id"],
        "message": f"Contract '{created['title']}' created",
        "actor": user.email, "created_at": _now(),
    })
    return created


@router.get("/dashboard")
async def dashboard(user: UserDep):
    db = get_db()
    contracts = await db.contracts.find({"tenant_id": user.tenant_id}, {"_id": 0}).to_list(length=2000)
    active = [c for c in contracts if c.get("status") in ("sent", "viewed", "pending_review", "draft")]
    signed = [c for c in contracts if c.get("status") in ("signed", "completed")]
    pending = [c for c in contracts if c.get("status") in ("sent", "viewed", "pending_review")]
    today = date.today().isoformat()
    expiring = [c for c in active if c.get("expires_at") and c["expires_at"] >= today
                and (datetime.fromisoformat(c["expires_at"]).date() - date.today()).days <= 14]
    revenue = sum(c.get("contract_amount") or 0 for c in signed)
    total_value = sum(c.get("contract_amount") or 0 for c in contracts)
    # Monthly buckets (last 6)
    buckets: dict[str, dict] = {}
    for c in contracts:
        m = (c.get("created_at") or "")[:7]
        if not m:
            continue
        b = buckets.setdefault(m, {"month": m, "created": 0, "signed": 0, "value": 0.0})
        b["created"] += 1
        if c.get("status") in ("signed", "completed"):
            b["signed"] += 1
            b["value"] += c.get("contract_amount") or 0
    months = sorted(buckets.values(), key=lambda b: b["month"])[-6:]
    return {
        "active_count": len(active),
        "signed_count": len(signed),
        "expiring_count": len(expiring),
        "pending_signature_count": len(pending),
        "total_count": len(contracts),
        "revenue": round(revenue, 2),
        "total_value": round(total_value, 2),
        "monthly": months,
    }


@router.get("/{cid}")
async def get_contract(cid: str, user: UserDep):
    c = await _ct_repo().get(user.tenant_id, cid)
    if not c:
        raise HTTPException(404, "Contract not found")
    if _is_expired(c) and c.get("status") not in ("expired", "signed", "completed"):
        c["status"] = "expired"
    return c


@router.patch("/{cid}")
async def update_contract(cid: str, body: ContractIn, user: UserDep):
    db = get_db()
    existing = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not existing:
        raise HTTPException(404, "Contract not found")
    if existing.get("status") in ("signed", "completed"):
        raise HTTPException(400, "Signed contracts cannot be edited")
    data = body.model_dump()
    # keep snapshot: re-snapshot only if client_id changes
    if data.get("client_id") and data["client_id"] != existing.get("client_id"):
        client = await db.clients.find_one({"tenant_id": user.tenant_id, "id": data["client_id"]}, {"_id": 0})
        if not client:
            raise HTTPException(400, "Client not found")
        data["client_snapshot"] = _client_snapshot(client)
    else:
        data["client_snapshot"] = existing.get("client_snapshot")
    data["version"] = int(existing.get("version", 1)) + 1
    updated = await _ct_repo().update(user.tenant_id, cid, data)
    await _push_version(db, updated, user.email, "updated")
    await _audit(db, updated, "updated", user.email)
    return updated


@router.post("/{cid}/send")
async def send_contract(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") in ("signed", "completed"):
        raise HTTPException(400, "Contract is already signed")
    token = c.get("share_token") or secrets.token_urlsafe(24)
    await db.contracts.update_one(
        {"tenant_id": user.tenant_id, "id": cid},
        {"$set": {"share_token": token, "status": "sent",
                  "sent_at": _now(), "updated_at": _now()}},
    )
    c2 = {**c, "share_token": token, "status": "sent"}
    await _audit(db, c2, "sent", user.email)
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return {"share_token": token, "public_url": f"{base}/public/contract/{token}"}


@router.post("/{cid}/reminder", status_code=204)
async def send_reminder(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") not in ("sent", "viewed", "pending_review"):
        raise HTTPException(400, "Only sent or viewed contracts can receive reminders")
    await _audit(db, c, "reminder_sent", user.email)
    return None


@router.get("/{cid}/audit")
async def get_audit(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    events = await db.contract_audit.find(
        {"tenant_id": user.tenant_id, "contract_id": cid}, {"_id": 0}
    ).sort([("created_at", 1)]).to_list(length=500)
    return events


@router.get("/{cid}/versions")
async def list_versions(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    versions = await db.contract_versions.find(
        {"tenant_id": user.tenant_id, "contract_id": cid}, {"_id": 0}
    ).sort([("created_at", -1)]).to_list(length=200)
    return versions


@router.post("/{cid}/versions/{vid}/restore")
async def restore_version(cid: str, vid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") in ("signed", "completed"):
        raise HTTPException(400, "Signed contracts cannot be restored")
    v = await db.contract_versions.find_one(
        {"tenant_id": user.tenant_id, "contract_id": cid, "id": vid}, {"_id": 0}
    )
    if not v:
        raise HTTPException(404, "Version not found")
    snap = v.get("snapshot", {})
    updates = {**snap, "version": int(c.get("version", 1)) + 1, "updated_at": _now()}
    await db.contracts.update_one({"tenant_id": user.tenant_id, "id": cid}, {"$set": updates})
    restored = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid}, {"_id": 0})
    await _push_version(db, restored, user.email, f"restored from {vid}")
    await _audit(db, restored, "restored", user.email, {"from_version": vid})
    return restored


@router.post("/{cid}/cancel")
async def cancel_contract(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") in ("signed", "completed"):
        raise HTTPException(400, "Signed contracts cannot be cancelled")
    await db.contracts.update_one(
        {"tenant_id": user.tenant_id, "id": cid},
        {"$set": {"status": "cancelled", "updated_at": _now()}},
    )
    await _audit(db, c, "cancelled", user.email)
    return {"status": "cancelled"}


@router.get("/{cid}/pdf")
async def contract_pdf(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contract not found")
    tenant = await db.tenants.find_one({"id": user.tenant_id}, {"_id": 0}) or {}
    pdf = _render_pdf(c, tenant)
    fname = (c.get("title") or "contract").replace(" ", "_")
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.delete("/{cid}", status_code=204)
async def delete_contract(cid: str, user: UserDep):
    await _ct_repo().delete(user.tenant_id, cid)


# ---------------------------- Public sign flow -------------------------------
@public_router.get("/{token}")
async def public_get_contract(token: str, request: Request):
    db = get_db()
    c = await db.contracts.find_one({"share_token": token}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contract not found")
    if _is_expired(c) and c.get("status") not in ("expired", "signed", "completed"):
        c["status"] = "expired"
    # Mark viewed once
    if c.get("status") in ("sent",):
        await db.contracts.update_one(
            {"id": c["id"]},
            {"$set": {"status": "viewed", "viewed_at": _now(), "updated_at": _now()}},
        )
        c["status"] = "viewed"
        c["viewed_at"] = _now()
        await _audit(db, c, "viewed", "client",
                     {"ip": request.client.host if request.client else None,
                      "ua": request.headers.get("user-agent", "")})
    tenant = await db.tenants.find_one({"id": c["tenant_id"]}, {"_id": 0, "modules": 0}) or {}
    tenant_pub = {
        "name": tenant.get("name"),
        "logo_url": tenant.get("logo_url"),
        "address": tenant.get("address"),
        "website": tenant.get("website"),
    }
    variables = _build_variables(c, tenant)
    c["rendered_html"] = _resolve_variables(c.get("body_html", ""), variables)
    return {"contract": c, "tenant": tenant_pub}


@public_router.get("/{token}/pdf")
async def public_pdf(token: str):
    db = get_db()
    c = await db.contracts.find_one({"share_token": token}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contract not found")
    tenant = await db.tenants.find_one({"id": c["tenant_id"]}, {"_id": 0}) or {}
    pdf = _render_pdf(c, tenant)
    fname = (c.get("title") or "contract").replace(" ", "_")
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@public_router.post("/{token}/sign")
async def public_sign(token: str, body: SignIn, request: Request):
    if not body.consent:
        raise HTTPException(400, "Consent required")
    if body.signature_type not in ("typed", "drawn"):
        raise HTTPException(400, "signature_type must be 'typed' or 'drawn'")
    if body.signature_type == "drawn" and not body.signature_data:
        raise HTTPException(400, "signature_data required for drawn signature")

    db = get_db()
    c = await db.contracts.find_one({"share_token": token})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") in ("signed", "completed"):
        raise HTTPException(409, "Already signed")
    if _is_expired(c):
        raise HTTPException(410, "This contract has expired")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")
    signature = {
        "signer_name": body.signer_name,
        "signer_email": body.signer_email,
        "signature_type": body.signature_type,
        "signature_data": body.signature_data,
        "signed_at": _now(),
        "ip": ip, "user_agent": ua,
    }
    await db.contracts.update_one(
        {"id": c["id"]},
        {"$set": {"status": "signed", "signature": signature,
                  "signed_at": _now(), "updated_at": _now()}},
    )
    signed_c = {**c, "status": "signed", "signature": signature}
    await _audit(db, signed_c, "signed", body.signer_name, {"ip": ip, "ua": ua})
    await db.activities.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": c["tenant_id"],
        "type": "contract_signed",
        "entity_id": c.get("client_id") or c["id"],
        "message": f"Contract '{c.get('title','')}' signed by {body.signer_name}",
        "actor": body.signer_name, "created_at": _now(),
    })
    return {"ok": True, "signed_at": signature["signed_at"]}


@public_router.post("/{token}/reject")
async def public_reject(token: str, body: RejectIn, request: Request):
    db = get_db()
    c = await db.contracts.find_one({"share_token": token})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") in ("signed", "completed"):
        raise HTTPException(409, "Already signed — cannot reject")
    await db.contracts.update_one(
        {"id": c["id"]},
        {"$set": {"status": "cancelled",
                  "rejection": {"reason": body.reason, "by": body.signer_name,
                                "at": _now()},
                  "updated_at": _now()}},
    )
    await _audit(db, c, "rejected", body.signer_name or "client",
                 {"reason": body.reason})
    return {"ok": True}


@public_router.post("/{token}/comment", status_code=201)
async def public_comment(token: str, body: CommentIn, request: Request):
    db = get_db()
    c = await db.contracts.find_one({"share_token": token})
    if not c:
        raise HTTPException(404, "Contract not found")
    cm = {"id": new_id(), "author": body.author, "body": body.body,
          "at": _now(),
          "ip": request.client.host if request.client else None}
    await db.contracts.update_one({"id": c["id"]}, {"$push": {"comments": cm}})
    await _audit(db, c, "commented", body.author, {"body": body.body[:200]})
    return cm


# ---------------------------- PDF rendering ----------------------------------
def _qr_png(data: str) -> bytes:
    import qrcode
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _html_to_paragraphs(html: str) -> list[tuple[str, str]]:
    """Very small HTML → (style, text) converter for reportlab.

    Handles h1/h2/h3, p, ul/ol/li, strong/em/u, br. Anything else is stripped.
    """
    if not html:
        return []
    text = html
    # Remove script/style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.S | re.I)
    # Normalize <br>
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    # Split into block chunks by heading/paragraph/list-item tags
    blocks: list[tuple[str, str]] = []
    pattern = re.compile(
        r"<(h1|h2|h3|p|li|blockquote)[^>]*>(.*?)</\1>",
        re.S | re.I,
    )
    for m in pattern.finditer(text):
        tag = m.group(1).lower()
        inner = m.group(2)
        # Preserve <strong>/<em>/<u>/<b>/<i> for reportlab
        inner = re.sub(r"</?strong>", lambda mm: "<b>" if not mm.group(0).startswith("</") else "</b>", inner, flags=re.I)
        inner = re.sub(r"</?em>", lambda mm: "<i>" if not mm.group(0).startswith("</") else "</i>", inner, flags=re.I)
        # Strip all other tags
        inner = re.sub(r"<(?!/?(b|i|u|br))[^>]+>", "", inner)
        inner = inner.replace("&nbsp;", " ").strip()
        if not inner:
            continue
        if tag in ("h1", "h2", "h3"):
            blocks.append((tag, inner))
        elif tag == "li":
            blocks.append(("li", inner))
        elif tag == "blockquote":
            blocks.append(("bq", inner))
        else:
            blocks.append(("p", inner))
    if not blocks:  # fallback: treat whole text as one paragraph
        plain = re.sub(r"<[^>]+>", "", text).strip()
        if plain:
            blocks.append(("p", plain))
    return blocks


def _render_pdf(contract: dict, tenant: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
        PageBreak, ListFlowable, ListItem, KeepTogether,
    )
    from reportlab.pdfgen.canvas import Canvas

    variables = _build_variables(contract, tenant)
    body_html = _resolve_variables(contract.get("body_html", ""), variables)
    blocks = _html_to_paragraphs(body_html)

    verification_id = contract.get("verification_id") or "—"
    frontend = os.environ.get("FRONTEND_URL", "").rstrip("/")
    verify_url = f"{frontend}/public/contract/{contract.get('share_token','')}"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        title=contract.get("title", "Contract"),
        author=tenant.get("name", "NED Tech"),
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.6 * cm, bottomMargin=2.2 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="h1_c", parent=styles["Heading1"], fontSize=20, spaceAfter=10, textColor=colors.HexColor("#0a0a0a")))
    styles.add(ParagraphStyle(name="h2_c", parent=styles["Heading2"], fontSize=15, spaceAfter=8, textColor=colors.HexColor("#171717")))
    styles.add(ParagraphStyle(name="h3_c", parent=styles["Heading3"], fontSize=12, spaceAfter=6, textColor=colors.HexColor("#171717")))
    styles.add(ParagraphStyle(name="body_c", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=6, textColor=colors.HexColor("#171717")))
    styles.add(ParagraphStyle(name="li_c", parent=styles["BodyText"], fontSize=10.5, leading=15, bulletIndent=8, leftIndent=18))
    styles.add(ParagraphStyle(name="bq_c", parent=styles["BodyText"], fontSize=10.5, leading=15, leftIndent=18, textColor=colors.HexColor("#525252")))
    styles.add(ParagraphStyle(name="sig_c", fontName="Helvetica-Oblique", fontSize=22))
    styles.add(ParagraphStyle(name="muted_c", fontSize=8.5, textColor=colors.HexColor("#737373")))

    story: list = []

    # Header block (tenant + client)
    snap = contract.get("client_snapshot") or {}
    top_data = [[
        Paragraph(f"<b>{tenant.get('name','Company')}</b><br/>"
                  f"{tenant.get('address','') or ''}<br/>"
                  f"{tenant.get('website','') or ''}", styles["body_c"]),
        Paragraph(f"<b>Prepared for</b><br/>"
                  f"{snap.get('company','') or snap.get('client_name','')}<br/>"
                  f"{snap.get('contact_person','') or ''}<br/>"
                  f"{snap.get('email','') or ''}<br/>"
                  f"{snap.get('address','') or ''}<br/>"
                  f"{'VAT: ' + snap.get('vat_number') if snap.get('vat_number') else ''}",
                  styles["body_c"]),
    ]]
    t = Table(top_data, colWidths=[8.5 * cm, 8.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(contract.get("title", "Contract"), styles["h1_c"]))
    story.append(Paragraph(
        f"Verification ID: <b>{verification_id}</b> &nbsp;·&nbsp; "
        f"Issued: {date.today().isoformat()}"
        + (f" &nbsp;·&nbsp; Amount: {variables.get('contract_amount')}" if variables.get("contract_amount") else ""),
        styles["muted_c"]))
    story.append(Spacer(1, 14))

    # Body
    li_buffer: list = []
    for tag, inner in blocks:
        if tag == "li":
            li_buffer.append(ListItem(Paragraph(inner, styles["body_c"]), leftIndent=10))
            continue
        if li_buffer:
            story.append(ListFlowable(li_buffer, bulletType="bullet", start="•", leftIndent=20))
            li_buffer = []
        if tag == "h1":
            story.append(Paragraph(inner, styles["h1_c"]))
        elif tag == "h2":
            story.append(Paragraph(inner, styles["h2_c"]))
        elif tag == "h3":
            story.append(Paragraph(inner, styles["h3_c"]))
        elif tag == "bq":
            story.append(Paragraph(inner, styles["bq_c"]))
        else:
            story.append(Paragraph(inner, styles["body_c"]))
    if li_buffer:
        story.append(ListFlowable(li_buffer, bulletType="bullet", start="•", leftIndent=20))

    # Signature block
    story.append(Spacer(1, 18))
    story.append(Paragraph("<b>Signatures</b>", styles["h3_c"]))
    sig = contract.get("signature") or {}
    if sig:
        if sig.get("signature_type") == "drawn" and sig.get("signature_data"):
            try:
                b64 = sig["signature_data"].split(",", 1)[-1]
                img = Image(BytesIO(base64.b64decode(b64)), width=6 * cm, height=2 * cm)
                story.append(img)
            except Exception:
                story.append(Paragraph(sig.get("signer_name", ""), styles["sig_c"]))
        else:
            story.append(Paragraph(sig.get("signer_name", ""), styles["sig_c"]))
        story.append(Paragraph(
            f"{sig.get('signer_name','')}<br/>"
            f"Signed on {sig.get('signed_at','')}<br/>"
            f"IP: {sig.get('ip','')}",
            styles["muted_c"]))
    else:
        story.append(Paragraph("_________________________________<br/>Client signature (pending)",
                               styles["muted_c"]))

    # Footer with QR code — drawn via canvas hook
    def on_page(canvas: Canvas, doc):
        page = canvas.getPageNumber()
        w, h = A4
        # Header line
        canvas.setStrokeColor(colors.HexColor("#e5e5e5"))
        canvas.line(2 * cm, h - 2 * cm, w - 2 * cm, h - 2 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#525252"))
        canvas.drawString(2 * cm, h - 1.5 * cm, tenant.get("name", "Company"))
        canvas.drawRightString(w - 2 * cm, h - 1.5 * cm,
                               contract.get("title", "Contract"))
        # Footer
        canvas.setStrokeColor(colors.HexColor("#e5e5e5"))
        canvas.line(2 * cm, 1.8 * cm, w - 2 * cm, 1.8 * cm)
        canvas.setFillColor(colors.HexColor("#525252"))
        canvas.drawString(2 * cm, 1.3 * cm,
                          f"Verification ID: {verification_id}")
        canvas.drawCentredString(w / 2, 1.3 * cm,
                                 f"Page {page}")
        canvas.drawRightString(w - 2 * cm, 1.3 * cm,
                               tenant.get("website", "") or "")
        # QR code — only on last page bottom-right (approx: always draw small)
        try:
            from reportlab.lib.utils import ImageReader
            qr = ImageReader(BytesIO(_qr_png(verify_url or verification_id)))
            canvas.drawImage(qr, w - 3.2 * cm, 2.0 * cm,
                             width=1.2 * cm, height=1.2 * cm, mask="auto")
        except Exception as e:
            pass

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
