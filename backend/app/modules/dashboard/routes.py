"""Dashboard aggregation endpoint."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter

from app.core.database import get_db
from app.core.deps import UserDep

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def overview(user: UserDep):
    db = get_db()
    tid = user.tenant_id

    # Counts
    active_clients = await db.clients.count_documents({"tenant_id": tid, "status": {"$ne": "inactive"}})
    open_tasks = await db.tasks.count_documents({"tenant_id": tid, "status": {"$ne": "done"}})

    # Upcoming invoices
    now = datetime.now(timezone.utc)
    thirty = (now + timedelta(days=30)).isoformat()
    upcoming = await db.invoices.find(
        {"tenant_id": tid, "status": {"$in": ["sent", "draft"]}},
        {"_id": 0, "id": 1, "number": 1, "client_name": 1, "due_date": 1, "items": 1, "currency": 1}
    ).sort([("due_date", 1)]).limit(6).to_list(length=6)
    for inv in upcoming:
        items = inv.pop("items", [])
        total = sum(i.get("quantity", 0) * i.get("unit_price", 0) * (1 + i.get("tax_rate", 0) / 100) for i in items)
        inv["amount"] = round(total, 2)

    # Finance summary
    invoices = await db.invoices.find({"tenant_id": tid}, {"_id": 0}).to_list(length=5000)
    expenses = await db.expenses.find({"tenant_id": tid}, {"_id": 0}).to_list(length=5000)
    revenue = 0.0
    for inv in invoices:
        if inv.get("status") == "paid":
            revenue += sum(i.get("quantity", 0) * i.get("unit_price", 0) * (1 + i.get("tax_rate", 0) / 100) for i in inv.get("items", []))
    exp = sum(e.get("amount", 0) * (1 + e.get("tax_rate", 0) / 100) for e in expenses)

    # Pipeline
    deals = await db.deals.find({"tenant_id": tid}, {"_id": 0}).to_list(length=5000)
    pipeline_value = sum(d.get("value", 0) for d in deals if d.get("stage") not in ("won", "lost"))
    won_value = sum(d.get("value", 0) for d in deals if d.get("stage") == "won")

    # 6-month revenue trend (based on paid invoices' updated_at)
    months = []
    labels = []
    for i in range(5, -1, -1):
        month = (now.replace(day=1) - timedelta(days=30 * i))
        labels.append(month.strftime("%b"))
        months.append((month.strftime("%Y-%m"), 0.0))
    m_dict = {k: v for k, v in months}
    for inv in invoices:
        if inv.get("status") != "paid":
            continue
        d = (inv.get("updated_at") or inv.get("created_at") or "")[:7]
        if d in m_dict:
            m_dict[d] += sum(i.get("quantity", 0) * i.get("unit_price", 0) * (1 + i.get("tax_rate", 0) / 100) for i in inv.get("items", []))
    trend = [{"month": labels[idx], "revenue": round(m_dict[k], 2), "expenses": 0.0} for idx, (k, _) in enumerate(months)]

    # Recent activity
    activity = await db.activities.find({"tenant_id": tid}, {"_id": 0}).sort([("created_at", -1)]).limit(10).to_list(length=10)

    return {
        "kpis": {
            "revenue": round(revenue, 2),
            "expenses": round(exp, 2),
            "profit": round(revenue - exp, 2),
            "active_clients": active_clients,
            "open_tasks": open_tasks,
            "pipeline_value": round(pipeline_value, 2),
            "won_value": round(won_value, 2),
        },
        "upcoming_invoices": upcoming,
        "trend": trend,
        "activity": activity,
    }
