"""Subscription & billing (FR-011) — Razorpay adapter, plan catalog, usage metering.

Mock provider lets the full upgrade/usage/limit flow run without Razorpay keys. Webhook
verification uses the configured secret when present.
"""
from __future__ import annotations

import hashlib
import hmac

from app.core.config import settings
from app.models.billing import PLAN_FREE, PLAN_PRO, PLAN_STARTER

# Plan catalog (SRS FR-011 / §1.2 pricing ₹199–₹799).
PLANS: dict[str, dict] = {
    PLAN_FREE: {
        "name": "Free",
        "price_inr": 0,
        "monthly_scans": 20,
        "features": ["20 invoice scans/month", "Basic dashboard", "GSTR preview"],
        "gstr_export": False,
        "reconciliation": False,
        "eway_bill": False,
        "priority_processing": False,
    },
    PLAN_STARTER: {
        "name": "Starter",
        "price_inr": 199,
        "monthly_scans": 500,
        "features": ["Unlimited invoices", "GSTR-1 & 3B export", "Basic reconciliation",
                     "WhatsApp + email alerts"],
        "gstr_export": True,
        "reconciliation": True,
        "eway_bill": False,
        "priority_processing": False,
    },
    PLAN_PRO: {
        "name": "Pro",
        "price_inr": 799,
        "monthly_scans": 5000,
        "features": ["Everything in Starter", "Advanced reconciliation", "E-way bills",
                     "Priority processing", "Dedicated support"],
        "gstr_export": True,
        "reconciliation": True,
        "eway_bill": True,
        "priority_processing": True,
    },
}

# Per-feature gates (FR-011): which plans may use a given capability.
FEATURE_PLANS = {
    "gstr_export": {PLAN_STARTER, PLAN_PRO},
    "reconciliation": {PLAN_STARTER, PLAN_PRO},
    "eway_bill": {PLAN_PRO},
}


def plan_allows(plan: str, feature: str) -> bool:
    return plan in FEATURE_PLANS.get(feature, set())


def scan_limit(plan: str) -> int:
    return PLANS.get(plan, PLANS[PLAN_FREE])["monthly_scans"]


def has_scan_quota(plan: str, scans_used: int, topup: int = 0) -> bool:
    return scans_used < scan_limit(plan) + topup


def create_checkout(plan: str, tenant_id: str) -> dict:
    """Create a subscription/checkout. Mock returns a fake order the frontend can 'pay'."""
    price = PLANS[plan]["price_inr"]
    provider = settings.RAZORPAY_PROVIDER.lower()
    if provider == "razorpay" and settings.RAZORPAY_KEY_ID:
        import razorpay  # imported lazily; only needed for live mode

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create(
            {"amount": price * 100, "currency": "INR", "notes": {"tenant_id": tenant_id,
                                                                 "plan": plan}}
        )
        return {"provider": "razorpay", "order_id": order["id"], "amount": price,
                "key_id": settings.RAZORPAY_KEY_ID}
    return {
        "provider": "mock",
        "order_id": f"order_mock_{tenant_id[:8]}_{plan}",
        "amount": price,
        "key_id": "rzp_test_mock",
        "note": "Mock checkout — POST /billing/confirm to activate the plan.",
    }


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return settings.is_dev  # accept in dev when unset
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
