"""Products & Services."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import BaseRepository

router = APIRouter(prefix="/products", tags=["Products"], dependencies=[Depends(module_gate("products"))])


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = "product"  # product | service
    sku: Optional[str] = None
    category: Optional[str] = None
    price: float = 0
    cost: float = 0
    currency: str = "USD"
    tax_rate: float = 0
    unit: Optional[str] = None
    description: Optional[str] = None
    active: bool = True


_repo: BaseRepository | None = None


def _get_repo():
    global _repo
    if _repo is None:
        _repo = BaseRepository(get_db(), ProductIn, "products")
    return _repo


@router.get("")
async def list_products(user: UserDep, kind: str | None = None):
    f = {"kind": kind} if kind else {}
    return await _get_repo().list(user.tenant_id, f, limit=500)


@router.post("", status_code=201)
async def create_product(body: ProductIn, user: UserDep):
    return await _get_repo().create(user.tenant_id, body.model_dump())


@router.patch("/{pid}")
async def update_product(pid: str, body: ProductIn, user: UserDep):
    d = await _get_repo().update(user.tenant_id, pid, body.model_dump())
    if not d: raise HTTPException(404, "Product not found")
    return d


@router.delete("/{pid}", status_code=204)
async def delete_product(pid: str, user: UserDep):
    await _get_repo().delete(user.tenant_id, pid)
