from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class DueItemOut(BaseModel):
    return_type: str
    period: str
    due_date: date
    days_remaining: int


class DashboardOut(BaseModel):
    compliance_score: int
    invoices_pending_review: int
    next_due: DueItemOut | None = None
    days_to_next_due: int | None = None
    estimated_tax_liability: float
    itc_available: float
    itc_claimed: float
    upcoming_due_dates: list[DueItemOut]
    sales_this_period: float
    purchases_this_period: float
    recent_activity: list[dict]


class NotificationOut(BaseModel):
    id: str
    category: str
    channel: str
    title: str
    body: str
    deep_link: str | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PnLOut(BaseModel):
    period_from: date
    period_to: date
    total_income: float
    total_expense: float
    net: float
    output_tax: float
    input_tax_credit: float
    net_gst_payable: float


class MessageOut(BaseModel):
    message: str
