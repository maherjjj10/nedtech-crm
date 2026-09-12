"""Dashboard aggregation endpoint."""
from datetime import datetime, timedelta, timezone
import asyncio

from fastapi import APIRouter

from app.core.database import get_db
from app.core.deps import UserDep

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def overview(user: UserDep):
    db = get_db()
    tid = user.tenant_id
    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # Basic counts
    # ---------------------------------------------------------

    active_clients_task = db.clients.count_documents({
        "tenant_id": tid,
        "status": {"$ne": "inactive"},
    })

    open_tasks_task = db.tasks.count_documents({
        "tenant_id": tid,
        "status": {"$ne": "done"},
    })

    # ---------------------------------------------------------
    # Upcoming invoices
    # ---------------------------------------------------------

    upcoming_task = (
        db.invoices.find(
            {
                "tenant_id": tid,
                "status": {"$in": ["sent", "draft"]},
            },
            {
                "_id": 0,
                "id": 1,
                "number": 1,
                "client_name": 1,
                "due_date": 1,
                "items": 1,
                "currency": 1,
            },
        )
        .sort([("due_date", 1)])
        .limit(6)
        .to_list(length=6)
    )

    # ---------------------------------------------------------
    # Finance summary
    #
    # IMPORTANT:
    # MongoDB calculates the totals directly.
    # We no longer download thousands of invoices/expenses.
    # ---------------------------------------------------------

    invoice_summary_task = db.invoices.aggregate([
        {
            "$match": {
                "tenant_id": tid,
                "status": "paid",
            }
        },
        {
            "$project": {
                "total": {
                    "$reduce": {
                        "input": {"$ifNull": ["$items", []]},
                        "initialValue": 0,
                        "in": {
                            "$add": [
                                "$$value",
                                {
                                    "$multiply": [
                                        {"$ifNull": ["$$this.quantity", 0]},
                                        {"$ifNull": ["$$this.unit_price", 0]},
                                        {
                                            "$add": [
                                                1,
                                                {
                                                    "$divide": [
                                                        {"$ifNull": ["$$this.tax_rate", 0]},
                                                        100,
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    }
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "revenue": {"$sum": "$total"},
            }
        },
    ]).to_list(length=1)

    expense_summary_task = db.expenses.aggregate([
        {
            "$match": {
                "tenant_id": tid,
            }
        },
        {
            "$project": {
                "total": {
                    "$multiply": [
                        {"$ifNull": ["$amount", 0]},
                        {
                            "$add": [
                                1,
                                {
                                    "$divide": [
                                        {"$ifNull": ["$tax_rate", 0]},
                                        100,
                                    ]
                                },
                            ]
                        },
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "expenses": {"$sum": "$total"},
            }
        },
    ]).to_list(length=1)

    # ---------------------------------------------------------
    # Pipeline
    # ---------------------------------------------------------

    pipeline_summary_task = db.deals.aggregate([
        {
            "$match": {
                "tenant_id": tid,
            }
        },
        {
            "$group": {
                "_id": None,
                "pipeline_value": {
                    "$sum": {
                        "$cond": [
                            {
                                "$not": [
                                    {
                                        "$in": [
                                            "$stage",
                                            ["won", "lost"],
                                        ]
                                    }
                                ]
                            },
                            {"$ifNull": ["$value", 0]},
                            0,
                        ]
                    }
                },
                "won_value": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$stage", "won"]},
                            {"$ifNull": ["$value", 0]},
                            0,
                        ]
                    }
                },
            }
        },
    ]).to_list(length=1)

    # ---------------------------------------------------------
    # 6-month revenue trend
    # ---------------------------------------------------------

    trend_task = db.invoices.aggregate([
        {
            "$match": {
                "tenant_id": tid,
                "status": "paid",
            }
        },
        {
            "$project": {
                "month": {
                    "$substr": [
                        {
                            "$ifNull": [
                                "$updated_at",
                                {"$ifNull": ["$created_at", ""]},
                            ]
                        },
                        0,
                        7,
                    ]
                },
                "total": {
                    "$reduce": {
                        "input": {"$ifNull": ["$items", []]},
                        "initialValue": 0,
                        "in": {
                            "$add": [
                                "$$value",
                                {
                                    "$multiply": [
                                        {"$ifNull": ["$$this.quantity", 0]},
                                        {"$ifNull": ["$$this.unit_price", 0]},
                                        {
                                            "$add": [
                                                1,
                                                {
                                                    "$divide": [
                                                        {"$ifNull": ["$$this.tax_rate", 0]},
                                                        100,
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    }
                },
            }
        },
        {
            "$group": {
                "_id": "$month",
                "revenue": {"$sum": "$total"},
            }
        },
    ]).to_list(length=12)

    # ---------------------------------------------------------
    # Recent activity
    # ---------------------------------------------------------

    activity_task = (
        db.activities.find(
            {"tenant_id": tid},
            {"_id": 0},
        )
        .sort([("created_at", -1)])
        .limit(10)
        .to_list(length=10)
    )

    # ---------------------------------------------------------
    # Run independent database operations together
    # ---------------------------------------------------------

    (
        active_clients,
        open_tasks,
        upcoming,
        invoice_summary,
        expense_summary,
        pipeline_summary,
        trend_data,
        activity,
    ) = await asyncio.gather(
        active_clients_task,
        open_tasks_task,
        upcoming_task,
        invoice_summary_task,
        expense_summary_task,
        pipeline_summary_task,
        trend_task,
        activity_task,
    )

    # ---------------------------------------------------------
    # Upcoming invoice amounts
    # ---------------------------------------------------------

    for inv in upcoming:
        items = inv.pop("items", [])
        total = sum(
            i.get("quantity", 0)
            * i.get("unit_price", 0)
            * (1 + i.get("tax_rate", 0) / 100)
            for i in items
        )
        inv["amount"] = round(total, 2)

    # ---------------------------------------------------------
    # Extract totals
    # ---------------------------------------------------------

    revenue = (
        invoice_summary[0].get("revenue", 0)
        if invoice_summary
        else 0
    )

    expenses = (
        expense_summary[0].get("expenses", 0)
        if expense_summary
        else 0
    )

    pipeline_value = (
        pipeline_summary[0].get("pipeline_value", 0)
        if pipeline_summary
        else 0
    )

    won_value = (
        pipeline_summary[0].get("won_value", 0)
        if pipeline_summary
        else 0
    )

    # ---------------------------------------------------------
    # Build 6-month trend
    # ---------------------------------------------------------

    trend_lookup = {
        item["_id"]: item.get("revenue", 0)
        for item in trend_data
        if item.get("_id")
    }

    months = []

    year = now.year
    month = now.month

    for offset in range(5, -1, -1):
        total_months = year * 12 + (month - 1) - offset
        y = total_months // 12
        m = total_months % 12 + 1

        key = f"{y:04d}-{m:02d}"

        month_date = datetime(y, m, 1)

        months.append({
            "month": month_date.strftime("%b"),
            "revenue": round(
                trend_lookup.get(key, 0),
                2,
            ),
            "expenses": 0.0,
        })

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "kpis": {
            "revenue": round(revenue, 2),
            "expenses": round(expenses, 2),
            "profit": round(revenue - expenses, 2),
            "active_clients": active_clients,
            "open_tasks": open_tasks,
            "pipeline_value": round(pipeline_value, 2),
            "won_value": round(won_value, 2),
        },
        "upcoming_invoices": upcoming,
        "trend": months,
        "activity": activity,
    }
