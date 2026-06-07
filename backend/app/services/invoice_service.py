"""Invoice domain helpers shared by routes & workers (FR-002–FR-005)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Subscription
from app.models.invoice import (
    PURCHASE,
    SALES,
    STATUS_CONFIRMED,
    STATUS_FAILED,
    STATUS_NEEDS_REVIEW,
    STATUS_PROCESSING,
    Invoice,
    LedgerEntry,
)
from app.services import gstin as gstin_svc


def apply_extraction(inv: Invoice, result: dict) -> None:
    """Write a pipeline result onto an Invoice row."""
    f = result["fields"]
    inv.extracted = f
    inv.confidence = result["confidence"]
    inv.anomalies = result["anomalies"]
    inv.overall_confidence = result["overall_confidence"]
    inv.dedupe_hash = result.get("dedupe_hash")

    inv.counterparty_gstin = f.get("counterparty_gstin")
    inv.counterparty_name = f.get("counterparty_name")
    inv.invoice_no = f.get("invoice_no")
    inv.invoice_date = date.fromisoformat(f["invoice_date"]) if f.get("invoice_date") else None
    inv.place_of_supply = f.get("place_of_supply")
    inv.line_items = f.get("line_items")
    inv.taxable_value = f.get("taxable_value", 0.0)
    inv.cgst = f.get("cgst", 0.0)
    inv.sgst = f.get("sgst", 0.0)
    inv.igst = f.get("igst", 0.0)
    inv.cess = f.get("cess", 0.0)
    inv.total_value = f.get("total_value", 0.0)
    inv.status = STATUS_NEEDS_REVIEW  # all extractions land in review before booking


def mark_failed(inv: Invoice, reason: str) -> None:
    inv.status = STATUS_FAILED
    inv.notes = (inv.notes or "") + f"\n[extraction failed] {reason}"


def recompute_from_line_items(inv: Invoice) -> None:
    """Re-run tax aggregation after user edits on the review screen (FR-004)."""
    from app.services.gst_calc import aggregate_invoice

    supplier_state = (
        gstin_svc.state_code(inv.counterparty_gstin) if inv.counterparty_gstin else None
    )
    totals = aggregate_invoice(
        inv.line_items or [],
        supplier_state_code=supplier_state,
        place_of_supply_code=inv.place_of_supply,
    )
    bk = totals.breakup
    inv.taxable_value = bk.taxable_value
    inv.cgst, inv.sgst, inv.igst, inv.cess = bk.cgst, bk.sgst, bk.igst, bk.cess
    inv.total_value = bk.total_value


async def confirm_to_ledger(db: AsyncSession, inv: Invoice) -> None:
    """Confirm an invoice and post a ledger entry (FR-005)."""
    inv.status = STATUS_CONFIRMED

    # Avoid double-posting if confirmed again.
    existing = await db.execute(select(LedgerEntry).where(LedgerEntry.invoice_id == inv.id))
    if existing.scalars().first() is not None:
        return

    tax = round(inv.cgst + inv.sgst + inv.igst + inv.cess, 2)
    entry = LedgerEntry(
        tenant_id=inv.tenant_id,
        invoice_id=inv.id,
        entry_type=SALES if inv.direction == SALES else PURCHASE,
        entry_date=inv.invoice_date or date.today(),
        party_name=inv.counterparty_name,
        party_gstin=inv.counterparty_gstin,
        taxable_value=inv.taxable_value,
        tax_amount=tax,
        total_value=inv.total_value,
        sign=1 if inv.direction == SALES else -1,
        narration=f"{inv.direction.title()} - {inv.invoice_no or 'NA'}",
    )
    db.add(entry)
    await db.flush()


async def get_or_create_subscription(db: AsyncSession, tenant_id: str) -> Subscription:
    res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    sub = res.scalars().first()
    if sub is None:
        sub = Subscription(tenant_id=tenant_id)
        db.add(sub)
        await db.flush()
    return sub


# Re-export for route convenience
PROCESSING = STATUS_PROCESSING
