"""Contracts & E-Signatures.

Simple typed signature: signer enters their full name and confirms consent;
we store the signed_at + IP + user-agent as evidence and render the typed
signature in an italic script font in the PDF. Not DocuSign-grade but adequate
for standard SMB engagements.

Contract statuses: draft | sent | signed | expired
"""
import os
import secrets
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional

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


# ---------- Models ----------
class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    body_markdown: str


class ContractIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    template_id: Optional[str] = None
    body_markdown: str
    expires_at: Optional[str] = None   # YYYY-MM-DD; contract auto-expires after this


class SignIn(BaseModel):
    signer_name: str = Field(min_length=1, max_length=120)
    signer_email: Optional[str] = None
    consent: bool = True


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


def _is_expired(c: dict) -> bool:
    if c.get("status") == "signed" or not c.get("expires_at"):
        return False
    try:
        return datetime.now(timezone.utc).date().isoformat() > c["expires_at"]
    except Exception:
        return False


# ---------- Templates ----------
@router.get("/templates")
async def list_templates(user: UserDep):
    return await _tpl_repo().list(user.tenant_id, limit=200)


@router.post("/templates", status_code=201)
async def create_template(body: TemplateIn, user: UserDep):
    return await _tpl_repo().create(user.tenant_id, body.model_dump())


@router.patch("/templates/{tid}")
async def update_template(tid: str, body: TemplateIn, user: UserDep):
    t = await _tpl_repo().update(user.tenant_id, tid, body.model_dump())
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.delete("/templates/{tid}", status_code=204)
async def delete_template(tid: str, user: UserDep):
    await _tpl_repo().delete(user.tenant_id, tid)


# ---------- Contracts ----------
@router.get("")
async def list_contracts(user: UserDep, client_id: str | None = None):
    filters = {"client_id": client_id} if client_id else {}
    contracts = await _ct_repo().list(user.tenant_id, filters, limit=500)
    for c in contracts:
        if _is_expired(c) and c.get("status") not in ("expired", "signed"):
            c["status"] = "expired"
    return contracts


@router.post("", status_code=201)
async def create_contract(body: ContractIn, user: UserDep):
    data = body.model_dump()
    data["status"] = "draft"
    return await _ct_repo().create(user.tenant_id, data)


@router.get("/{cid}")
async def get_contract(cid: str, user: UserDep):
    c = await _ct_repo().get(user.tenant_id, cid)
    if not c:
        raise HTTPException(404, "Contract not found")
    if _is_expired(c) and c.get("status") not in ("expired", "signed"):
        c["status"] = "expired"
    return c


@router.patch("/{cid}")
async def update_contract(cid: str, body: ContractIn, user: UserDep):
    c = await _ct_repo().update(user.tenant_id, cid, body.model_dump())
    if not c:
        raise HTTPException(404, "Contract not found")
    return c


@router.post("/{cid}/send")
async def send_contract(cid: str, user: UserDep):
    db = get_db()
    c = await db.contracts.find_one({"tenant_id": user.tenant_id, "id": cid})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") == "signed":
        raise HTTPException(400, "Contract is already signed")
    token = c.get("share_token") or secrets.token_urlsafe(24)
    await db.contracts.update_one(
        {"tenant_id": user.tenant_id, "id": cid},
        {"$set": {"share_token": token, "status": "sent", "updated_at": utcnow_iso()}},
    )
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return {"share_token": token, "public_url": f"{base}/public/contract/{token}"}


@router.get("/{cid}/pdf")
async def contract_pdf(cid: str, user: UserDep):
    c = await get_db().contracts.find_one({"tenant_id": user.tenant_id, "id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contract not found")
    tenant = await get_db().tenants.find_one({"id": user.tenant_id}, {"_id": 0}) or {}
    pdf = _render_pdf(c, tenant)
    fname = (c.get("title") or "contract").replace(" ", "_")
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.delete("/{cid}", status_code=204)
async def delete_contract(cid: str, user: UserDep):
    await _ct_repo().delete(user.tenant_id, cid)


# ---------- Public sign flow ----------
@public_router.get("/{token}")
async def public_get_contract(token: str):
    db = get_db()
    c = await db.contracts.find_one({"share_token": token}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contract not found")
    if _is_expired(c) and c.get("status") not in ("expired", "signed"):
        c["status"] = "expired"
    tenant = await db.tenants.find_one({"id": c["tenant_id"]}, {"_id": 0, "modules": 0}) or {}
    return {"contract": c,
            "tenant": {"name": tenant.get("name"), "logo_url": tenant.get("logo_url"),
                       "address": tenant.get("address")}}


@public_router.post("/{token}/sign")
async def public_sign(token: str, body: SignIn, request: Request):
    if not body.consent:
        raise HTTPException(400, "Consent required")
    db = get_db()
    c = await db.contracts.find_one({"share_token": token})
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.get("status") == "signed":
        raise HTTPException(409, "Already signed")
    if _is_expired(c):
        raise HTTPException(410, "This contract has expired")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")
    signature = {
        "signer_name": body.signer_name,
        "signer_email": body.signer_email,
        "signed_at": utcnow_iso(),
        "ip": ip, "user_agent": ua,
    }
    await db.contracts.update_one(
        {"id": c["id"]},
        {"$set": {"status": "signed", "signature": signature, "updated_at": utcnow_iso()}},
    )
    await db.activities.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": c["tenant_id"],
        "type": "contract_signed", "entity_id": c["id"],
        "message": f"Contract '{c.get('title','')}' signed by {body.signer_name}",
        "actor": body.signer_name, "created_at": utcnow_iso(),
    })
    return {"ok": True, "signed_at": signature["signed_at"]}


def _render_pdf(contract: dict, tenant: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=contract.get("title", "Contract"))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="sig", fontName="Helvetica-Oblique",
                              fontSize=22, textColor=colors.black))
    story = [
        Paragraph(f"<b>{tenant.get('name','Company')}</b>", styles["Title"]),
        Paragraph(contract.get("title", "Contract"), styles["Heading2"]),
        Paragraph(f"Client: {contract.get('client_name','')}", styles["Normal"]),
        Spacer(1, 12),
    ]
    for para in (contract.get("body_markdown") or "").split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.replace("\n", "<br/>"), styles["Normal"]))
            story.append(Spacer(1, 6))

    sig = contract.get("signature")
    if sig:
        story.append(Spacer(1, 24))
        story.append(Paragraph("<b>Signature</b>", styles["Heading4"]))
        story.append(Paragraph(sig.get("signer_name", ""), styles["sig"]))
        story.append(Paragraph(
            f"Signed on {sig.get('signed_at','')} from IP {sig.get('ip','')}",
            styles["Italic"]))
    doc.build(story)
    return buf.getvalue()
