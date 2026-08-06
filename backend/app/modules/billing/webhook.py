"""Stripe webhook — path MUST be /api/stripe/webhook (Flow A default)."""
import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# NOTE: this router has NO prefix — mounted directly on the FastAPI app so the
# path resolves to exactly /api/stripe/webhook (matching Stripe registration).
webhook_router = APIRouter()


@webhook_router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Invalid signature")

    db = get_db()
    obj, t = event["data"]["object"], event["type"]
    now = datetime.now(timezone.utc).isoformat()

    if t == "checkout.session.completed":
        await db.payment_transactions.update_one(
            {"session_id": obj["id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": obj.get("payment_status", "paid"),
                      "stripe_subscription_id": obj.get("subscription"),
                      "stripe_payment_intent_id": obj.get("payment_intent"),
                      "updated_at": now}},
        )
        meta = obj.get("metadata", {}) or {}
        tenant_id = meta.get("tenant_id") or obj.get("client_reference_id")
        if tenant_id:
            await db.billing.update_one(
                {"tenant_id": tenant_id},
                {"$set": {"tenant_id": tenant_id, "plan": meta.get("lookup_key"),
                          "status": "active",
                          "stripe_subscription_id": obj.get("subscription"),
                          "stripe_customer_id": obj.get("customer"),
                          "updated_at": now}},
                upsert=True,
            )
    elif t == "checkout.session.async_payment_succeeded":
        await db.payment_transactions.update_one({"session_id": obj["id"]},
            {"$set": {"payment_status": "paid", "updated_at": now}})
    elif t in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        await db.payment_transactions.update_one({"session_id": obj["id"]},
            {"$set": {"status": "failed", "payment_status": "failed", "updated_at": now}})
    elif t in ("customer.subscription.updated", "customer.subscription.deleted"):
        meta = obj.get("metadata", {}) or {}
        tenant_id = meta.get("tenant_id")
        if tenant_id:
            status = "active" if t == "customer.subscription.updated" and obj.get("status") == "active" else obj.get("status", "canceled")
            await db.billing.update_one(
                {"tenant_id": tenant_id},
                {"$set": {"status": status, "updated_at": now}},
                upsert=True,
            )
    elif t == "charge.refunded":
        await db.payment_transactions.update_one(
            {"stripe_payment_intent_id": obj.get("payment_intent")},
            {"$set": {"status": "refunded", "payment_status": "refunded", "updated_at": now}},
        )
    return {"status": "ok"}
