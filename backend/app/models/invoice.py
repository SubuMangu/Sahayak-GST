"""Invoice & ledger models (FR-002 ingestion, FR-003/004 extraction/review, FR-005 ledger)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# Invoice direction
SALES = "sales"
PURCHASE = "purchase"

# Lifecycle status (FR-002 → FR-004)
STATUS_UPLOADED = "uploaded"
STATUS_PROCESSING = "processing"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_CONFIRMED = "confirmed"
STATUS_FAILED = "failed"

# Ingestion source
SOURCE_WEB = "web"
SOURCE_WHATSAPP = "whatsapp"


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    direction: Mapped[str] = mapped_column(String(10), default=PURCHASE)  # sales | purchase
    status: Mapped[str] = mapped_column(String(20), default=STATUS_UPLOADED, index=True)
    source: Mapped[str] = mapped_column(String(20), default=SOURCE_WEB)

    # Original file (encrypted at rest); we store the storage key, not the bytes.
    file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Extraction output (FR-003): full structured JSON + per-field confidence map.
    extracted: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    confidence: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    anomalies: Mapped[list | None] = mapped_column(SA_JSON, nullable=True)

    # Denormalised header fields for fast listing / GSTR generation (FR-006).
    counterparty_gstin: Mapped[str | None] = mapped_column(String(15), index=True, nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_no: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    place_of_supply: Mapped[str | None] = mapped_column(String(2), nullable=True)  # state code

    taxable_value: Mapped[float] = mapped_column(Float, default=0.0)
    cgst: Mapped[float] = mapped_column(Float, default=0.0)
    sgst: Mapped[float] = mapped_column(Float, default=0.0)
    igst: Mapped[float] = mapped_column(Float, default=0.0)
    cess: Mapped[float] = mapped_column(Float, default=0.0)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)

    # Line items: [{description, hsn, qty, rate, taxable_value, gst_rate, cgst, sgst, igst}]
    line_items: Mapped[list | None] = mapped_column(SA_JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_accountant_review: Mapped[bool] = mapped_column(default=False)

    # SHA-256 of normalised header → duplicate detection (FR-003).
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)


class LedgerEntry(Base, UUIDMixin, TimestampMixin):
    """Simplified double-entry style ledger (FR-005)."""

    __tablename__ = "ledger_entries"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)

    entry_type: Mapped[str] = mapped_column(String(20))  # sale | purchase | credit_note | debit_note
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    party_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    party_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)

    taxable_value: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    # +1 income/credit, -1 expense/debit — for simple P&L (FR-005).
    sign: Mapped[int] = mapped_column(Integer, default=1)
    narration: Mapped[str | None] = mapped_column(String(255), nullable=True)
