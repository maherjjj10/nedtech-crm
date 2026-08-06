"""Billing module: Stripe subscriptions (platform-managed sandbox)."""
import os
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import UserDep
from app.core.repository import new_id, utcnow_iso

router = APIRouter(tags=["Billing"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_ONBOARDING_URL = os.environ.get("STRIPE_ONBOARDING_URL", "")


PLANS = [
    {"lookup_key": "starter_monthly",  "name": "Starter",  "price_display": "$19/mo",
     "features": ["Up to 3 users", "Unlimited clients", "Sales pipeline", "Invoices & expenses", "Email support"]},
    {"lookup_key": "pro_monthly",      "name": "Pro",      "price_display": "$49/mo",
     "features": ["Up to 15 users", "Everything in Starter", "AI Assistant (GPT-5.4)", "Team invites", "Advanced reports"]},
    {"lookup_key": "business_monthly", "name": "Business", "price_display": "$129/mo",
     "features": ["Unlimited users", "Everything in Pro", "Priority support", "Custom modules", "API access"]},
]


class CheckoutRequest(BaseModel):
    lookup_key: str
    origin_url: str
    quantity: int = 1


@router.get("/billing/plans")
async def get_plans():
    """Return plans with live pricing from Stripe."""
    if not stripe.api_key:
        return {"plans": PLANS, "configured": False}
    out = []
    for p in PLANS:
        try:
            prices = stripe.Price.list(lookup_keys=[p["lookup_key"]], active=True, limit=1).data
            if prices:
                pr = prices[0]
                out.append({**p,
                    "amount": pr.unit_amount / 100 if pr.unit_amount else 0,
                    "currency": pr.currency, "interval": pr.recurring.interval if pr.recurring else None,
                    "price_id": pr.id, "product_id": pr.product})
            else:
                out.append(p)
        except Exception:
            out.append(p)
    return {"plans": out, "configured": True, "onboarding_url": STRIPE_ONBOARDING_URL}


@router.get("/billing/status")
async def billing_status(user: UserDep):
    doc = await get_db().billing.find_one({"tenant_id": user.tenant_id}, {"_id": 0})
    if not doc:
        return {"plan": None, "status": "free", "tenant_id": user.tenant_id}
    return doc


@router.post("/billing/checkout")
async def checkout(body: CheckoutRequest, user: UserDep):
    if not stripe.api_key:
        raise HTTPException(503, "Billing not configured")
    prices = stripe.Price.list(lookup_keys=[body.lookup_key], active=True, limit=1).data
    if not prices:
        raise HTTPException(400, f"Unknown plan: {body.lookup_key}")
    price = prices[0]

    kwargs = dict(
        line_items=[{"price": price.id, "quantity": body.quantity}],
        mode="subscription" if price.recurring else "payment",
        success_url=f"{body.origin_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/billing/cancel",
        client_reference_id=user.tenant_id,
        metadata={"tenant_id": user.tenant_id, "user_id": user.user_id, "lookup_key": body.lookup_key},
        subscription_data={"metadata": {"tenant_id": user.tenant_id, "lookup_key": body.lookup_key}},
    )
    try:
        session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
    except stripe.error.InvalidRequestError as e:
        msg = (getattr(e, "user_message", "") or "").lower()
        if "managed payments" in msg or "ineligible" in msg:
            session = stripe.checkout.Session.create(
                **kwargs, automatic_tax={"enabled": True}, billing_address_collection="required",
            )
        else:
            raise HTTPException(400, str(e))

    now = datetime.now(timezone.utc).isoformat()
    await get_db().payment_transactions.insert_one({
        "_id": session.id, "session_id": session.id,
        "tenant_id": user.tenant_id, "user_id": user.user_id,
        "lookup_key": body.lookup_key,
        "amount": (price.unit_amount or 0) * body.quantity, "currency": price.currency,
        "status": "initiated", "payment_status": "pending",
        "created_at": now, "updated_at": now,
    })
    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/billing/status/{session_id}")
async def session_status(session_id: str):
    db = get_db()
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Transaction not found")
    if record.get("payment_status") != "paid" and stripe.api_key:
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid",
                              "stripe_subscription_id": s.subscription,
                              "stripe_payment_intent_id": s.payment_intent,
                              "updated_at": utcnow_iso()}})
                if record.get("tenant_id"):
                    await db.billing.update_one(
                        {"tenant_id": record["tenant_id"]},
                        {"$set": {"tenant_id": record["tenant_id"], "plan": record.get("lookup_key"),
                                  "status": "active", "stripe_subscription_id": s.subscription,
                                  "stripe_customer_id": s.customer, "updated_at": utcnow_iso()}},
                        upsert=True,
                    )
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception:
            pass
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"]}
