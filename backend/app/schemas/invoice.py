from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str | None = None
    hsn: str | None = None
    qty: float | None = None
    rate: float | None = None
    taxable_value: float = 0.0
    gst_rate: float = 0.0


class InvoiceListItem(BaseModel):
    id: str
    direction: str
    status: str
    source: str
    counterparty_name: str | None = None
    counterparty_gstin: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    taxable_value: float
    total_value: float
    overall_confidence: float
    needs_accountant_review: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetail(InvoiceListItem):
    place_of_supply: str | None = None
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    cess: float = 0.0
    line_items: list[LineItem] | None = None
    extracted: dict | None = None
    confidence: dict | None = None
    anomalies: list[dict] | None = None
    file_name: str | None = None
    file_mime: str | None = None
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    """User corrections on the review screen (FR-004)."""

    counterparty_name: str | None = None
    counterparty_gstin: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    place_of_supply: str | None = None
    direction: str | None = None
    line_items: list[LineItem] | None = None
    notes: str | None = None
    needs_accountant_review: bool | None = None


class BulkApproveRequest(BaseModel):
    confidence_threshold: float = 0.85
    invoice_ids: list[str] | None = None  # if None, all eligible needs_review invoices


class InvoiceUploadResponse(BaseModel):
    id: str
    status: str
    overall_confidence: float
    needs_review: bool
    message: str
