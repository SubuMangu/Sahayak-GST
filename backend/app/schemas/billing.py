from __future__ import annotations

from pydantic import BaseModel


class PlanOut(BaseModel):
    code: str
    name: str
    price_inr: int
    monthly_scans: int
    features: list[str]


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    scans_used: int
    scan_limit: int
    invoices_processed: int
    topup_scans: int
    current_period_end: str | None = None

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    plan: str  # starter | pro


class CheckoutResponse(BaseModel):
    provider: str
    order_id: str
    amount: int
    key_id: str
    note: str | None = None


class ConfirmRequest(BaseModel):
    order_id: str
    plan: str
