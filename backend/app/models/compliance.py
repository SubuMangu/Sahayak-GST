"""Compliance models: GSTR filings, reconciliation, e-way bill (FR-006/007/008)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON as SA_JSON
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# GSTR filing status (FR-006)
GSTR_DRAFT = "draft"
GSTR_READY = "ready_for_filing"
GSTR_FILED = "filed"


class GSTRFiling(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "gstr_filings"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    return_type: Mapped[str] = mapped_column(String(12))  # GSTR1 | GSTR3B
    period: Mapped[str] = mapped_column(String(6), index=True)  # MMYYYY (GST portal format)
    status: Mapped[str] = mapped_column(String(20), default=GSTR_DRAFT)

    payload: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)  # portal-format JSON
    summary: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)  # human-readable totals
    is_nil: Mapped[bool] = mapped_column(default=False)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReconciliationRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reconciliation_runs"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    source: Mapped[str] = mapped_column(String(8))  # 2A | 2B
    period: Mapped[str] = mapped_column(String(6), index=True)
    summary: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)


class ReconItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recon_items"

    run_id: Mapped[str] = mapped_column(ForeignKey("reconciliation_runs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    # matched | missing_in_books | missing_in_portal | mismatch
    match_status: Mapped[str] = mapped_column(String(24), index=True)
    supplier_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    invoice_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    books_data: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    portal_data: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    tax_diff: Mapped[float] = mapped_column(Float, default=0.0)
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True)  # claimed/reconciled


class EwayBill(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eway_bills"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    ewb_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|generated|cancelled
    part_a: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    part_b: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
