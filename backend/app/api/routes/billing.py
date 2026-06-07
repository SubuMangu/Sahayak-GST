"""Billing & subscription routes (FR-011, US-10): plans, usage, checkout, webhook."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_tenant_context, require_owner
from app.models.billing import PLAN_FREE
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    ConfirmRequest,
    PlanOut,
    SubscriptionOut,
)
from app.schemas.common import MessageOut
from app.services import audit, billing
from app.services.billing import PLANS
from app.services.invoice_service import get_or_create_subscription

router = APIRouter()


@router.get("/plans", response_model=list[PlanOut])
async def list_plans():
    return [
        PlanOut(
            code=code,
            name=p["name"],
            price_inr=p["price_inr"],
            monthly_scans=p["monthly_scans"],
            features=p["features"],
        )
        for code, p in PLANS.items()
    ]


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    ctx: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db)
):
    sub = await get_or_create_subscription(db, ctx.tenant_id)
    return SubscriptionOut(
        plan=sub.plan,
        status=sub.status,
        scans_used=sub.scans_used,
        scan_limit=billing.scan_limit(sub.plan),
        invoices_processed=sub.invoices_processed,
        topup_scans=sub.topup_scans,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest,
    ctx: TenantContext = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    if payload.plan not in PLANS or payload.plan == PLAN_FREE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a paid plan.")
    order = billing.create_checkout(payload.plan, ctx.tenant_id)
    return CheckoutResponse(**order)


@router.post("/confirm", response_model=SubscriptionOut)
async def confirm_payment(
    payload: ConfirmRequest,
    ctx: TenantContext = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Activate a plan after (mock) payment success.

    In live mode this is driven by the Razorpay webhook; the mock flow lets the demo upgrade
    immediately after a 'checkout'.
    """
    if payload.plan not in PLANS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown plan.")
    sub = await get_or_create_subscription(db, ctx.tenant_id)
    sub.plan = payload.plan
    sub.status = "active"
    sub.scans_used = 0  # reset usage on new billing cycle
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    db.add(sub)
    await audit.log(db, action="billing.activate", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    detail=f"plan={payload.plan}")
    return SubscriptionOut(
        plan=sub.plan, status=sub.status, scans_used=sub.scans_used,
        scan_limit=billing.scan_limit(sub.plan), invoices_processed=sub.invoices_processed,
        topup_scans=sub.topup_scans,
        current_period_end=sub.current_period_end.isoformat(),
    )


@router.post("/webhook", response_model=MessageOut)
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Razorpay subscription lifecycle webhook (FR-011)."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not billing.verify_webhook_signature(body, signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature.")
    # Event handling (subscription.charged / payment.failed / etc.) would update the
    # Subscription row here keyed by razorpay_subscription_id. Acknowledged for the MVP.
    return MessageOut(message="ok")
