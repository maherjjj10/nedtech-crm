"""Global search module."""

from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.deps import UserDep, require_permission
from app.core.module_registry import module_gate


router = APIRouter(
    prefix="/search",
    tags=["Search"],
    dependencies=[
        Depends(module_gate("crm")),
        Depends(require_permission("crm")),
    ],
)


def _regex_search(fields: list[str], query: str):
    return {
        "$or": [
            {
                field: {
                    "$regex": query,
                    "$options": "i",
                }
            }
            for field in fields
        ]
    }


async def _search_collection(
    collection,
    tenant_id: str,
    query: str,
    fields: list[str],
    limit: int = 5,
):
    cursor = (
        collection.find(
            {
                "tenant_id": tenant_id,
                **_regex_search(fields, query),
            },
            {
                "_id": 0,
            },
        )
        .sort("_id", -1)
        .limit(limit)
    )

    return await cursor.to_list(length=limit)


@router.get("")
async def global_search(
    user: UserDep,
    q: str = Query(
        min_length=2,
        max_length=100,
    ),
):
    query = q.strip()

    if len(query) < 2:
        return {
            "clients": [],
            "suppliers": [],
            "products": [],
            "invoices": [],
            "quotes": [],
        }

    db = get_db()

    clients = await _search_collection(
        db.clients,
        user.tenant_id,
        query,
        [
            "name",
            "email",
            "company",
            "phone",
            "vat_number",
        ],
        limit=5,
    )

    suppliers = await _search_collection(
        db.suppliers,
        user.tenant_id,
        query,
        [
            "name",
            "company",
            "contact_person",
            "email",
            "phone",
            "vat_number",
            "kvk_number",
        ],
        limit=5,
    )

    products = await _search_collection(
        db.products,
        user.tenant_id,
        query,
        [
            "name",
            "sku",
            "category",
            "description",
        ],
        limit=5,
    )

    invoices = await _search_collection(
        db.invoices,
        user.tenant_id,
        query,
        [
            "number",
            "invoice_number",
            "client_name",
            "reference",
            "notes",
        ],
        limit=5,
    )

    quotes = await _search_collection(
        db.quotes,
        user.tenant_id,
        query,
        [
            "number",
            "quote_number",
            "client_name",
            "reference",
            "notes",
        ],
        limit=5,
    )

    return {
        "clients": clients,
        "suppliers": suppliers,
        "products": products,
        "invoices": invoices,
        "quotes": quotes,
    }