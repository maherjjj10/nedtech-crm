"""Client 360 subresources: notes, timeline, related deals/invoices."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import new_id, utcnow_iso

router = APIRouter(prefix="/clients", tags=["Client 360"], dependencies=[Depends(module_gate("crm"))])


class NoteIn(BaseModel):
    body: str


@router.get("/{client_id}/notes")
async def list_notes(client_id: str, user: UserDep):
    cur = get_db().client_notes.find(
        {"tenant_id": user.tenant_id, "client_id": client_id}, {"_id": 0}
    ).sort([("created_at", -1)])
    return await cur.to_list(length=200)


@router.post("/{client_id}/notes", status_code=201)
async def add_note(client_id: str, body: NoteIn, user: UserDep):
    db = get_db()
    if not await db.clients.find_one({"tenant_id": user.tenant_id, "id": client_id}):
        raise HTTPException(404, "Client not found")
    note_id = new_id()
    doc = {
        "_id": note_id, "id": note_id, "tenant_id": user.tenant_id,
        "client_id": client_id, "body": body.body,
        "author_email": user.email, "author_id": user.user_id,
        "created_at": utcnow_iso(),
    }
    await db.client_notes.insert_one(doc)
    await db.activities.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": user.tenant_id,
        "type": "client_note", "entity_id": client_id,
        "message": f"Note added to client", "actor": user.email,
        "created_at": utcnow_iso(),
    })
    return {k: v for k, v in doc.items() if k != "_id"}


@router.delete("/{client_id}/notes/{note_id}", status_code=204)
async def delete_note(client_id: str, note_id: str, user: UserDep):
    await get_db().client_notes.delete_one(
        {"tenant_id": user.tenant_id, "client_id": client_id, "id": note_id}
    )


@router.get("/{client_id}/timeline")
async def get_timeline(client_id: str, user: UserDep):
    db = get_db()
    client = await db.clients.find_one({"tenant_id": user.tenant_id, "id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(404, "Client not found")

    activities = await db.activities.find(
        {"tenant_id": user.tenant_id, "entity_id": client_id}, {"_id": 0}
    ).sort([("created_at", -1)]).to_list(length=200)

    deals = await db.deals.find(
        {"tenant_id": user.tenant_id, "$or": [{"client_id": client_id}, {"client_name": client.get("name")}]},
        {"_id": 0}
    ).sort([("created_at", -1)]).to_list(length=200)

    invoices = await db.invoices.find(
        {"tenant_id": user.tenant_id, "$or": [{"client_id": client_id}, {"client_name": client.get("name")}]},
        {"_id": 0}
    ).sort([("created_at", -1)]).to_list(length=200)

    for inv in invoices:
        total = sum(i.get("quantity", 0) * i.get("unit_price", 0) * (1 + i.get("tax_rate", 0) / 100)
                    for i in inv.get("items", []))
        inv["amount"] = round(total, 2)

    notes = await db.client_notes.find(
        {"tenant_id": user.tenant_id, "client_id": client_id}, {"_id": 0}
    ).sort([("created_at", -1)]).to_list(length=200)

    return {
        "client": client,
        "activities": activities,
        "deals": deals,
        "invoices": invoices,
        "notes": notes,
        "stats": {
            "deal_count": len(deals),
            "won_value": sum(d.get("value", 0) for d in deals if d.get("stage") == "won"),
            "invoice_count": len(invoices),
            "paid_value": sum(inv.get("amount", 0) for inv in invoices if inv.get("status") == "paid"),
            "outstanding": sum(inv.get("amount", 0) for inv in invoices if inv.get("status") in ("sent", "overdue")),
        },
    }
