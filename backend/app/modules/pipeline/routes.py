"""Sales pipeline: leads + deals with Kanban stages."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository

router = APIRouter(prefix="/pipeline", tags=["Sales Pipeline"], dependencies=[Depends(module_gate("sales"))])

DEFAULT_STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"]


class DealIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    value: float = 0
    currency: str = "USD"
    stage: str = "lead"
    probability: int = 20
    expected_close: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DealPatch(BaseModel):
    title: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    expected_close: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


_repo: BaseRepository | None = None


def _get_repo() -> BaseRepository:
    global _repo
    if _repo is None:
        _repo = BaseRepository(get_db(), DealIn, "deals")
    return _repo


@router.get("/stages")
async def get_stages(user: UserDep):
    return DEFAULT_STAGES


@router.get("/deals")
async def list_deals(user: UserDep, stage: str | None = None):
    filters = {"stage": stage} if stage else {}
    return await _get_repo().list(user.tenant_id, filters, limit=500)


@router.post("/deals", status_code=201)
async def create_deal(body: DealIn, user: UserDep):
    return await _get_repo().create(user.tenant_id, body.model_dump())


@router.get("/deals/{deal_id}")
async def get_deal(deal_id: str, user: UserDep):
    d = await _get_repo().get(user.tenant_id, deal_id)
    if not d:
        raise HTTPException(404, "Deal not found")
    return d


@router.patch("/deals/{deal_id}")
async def update_deal(deal_id: str, body: DealPatch, user: UserDep):
    d = await _get_repo().update(user.tenant_id, deal_id, body.model_dump())
    if not d:
        raise HTTPException(404, "Deal not found")
    return d


@router.delete("/deals/{deal_id}", status_code=204)
async def delete_deal(deal_id: str, user: UserDep):
    ok = await _get_repo().delete(user.tenant_id, deal_id)
    if not ok:
        raise HTTPException(404, "Deal not found")
    return None


@router.get("/summary")
async def pipeline_summary(user: UserDep):
    pipeline = [
        {"$match": {"tenant_id": user.tenant_id}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1},
            "value": {"$sum": "$value"},
        }},
    ]
    rows = await _get_repo().aggregate(pipeline)
    by_stage = {r["_id"]: {"count": r["count"], "value": r["value"]} for r in rows}
    return {"stages": DEFAULT_STAGES, "by_stage": by_stage}
