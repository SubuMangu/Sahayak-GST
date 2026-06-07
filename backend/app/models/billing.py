"""Subscription & usage models (FR-011 billing via Razorpay)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# Plans (SRS FR-011)
PLAN_FREE = "free"
PLAN_STARTER = "starter"
PLAN_PRO = "pro"


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True, unique=True)
    plan: Mapped[str] = mapped_column(String(20), default=PLAN_FREE)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|past_due|cancelled

    razorpay_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage metering for the current billing period (FR-011 usage visibility, US-10).
    scans_used: Mapped[int] = mapped_column(Integer, default=0)
    invoices_processed: Mapped[int] = mapped_column(Integer, default=0)
    topup_scans: Mapped[int] = mapped_column(Integer, default=0)


class UsageRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "usage_records"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    metric: Mapped[str] = mapped_column(String(40))  # invoice_scan | gstr_export | eway_bill
    quantity: Mapped[int] = mapped_column(Integer, default=1)
