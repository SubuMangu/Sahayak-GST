"""Dashboard & reporting routes (FR-009, US-02): KPIs, P&L, register exports."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_tenant_context
from app.models.business import Business
from app.models.compliance import GSTRFiling
from app.models.invoice import (
    PURCHASE,
    SALES,
    STATUS_CONFIRMED,
    STATUS_NEEDS_REVIEW,
    Invoice,
    LedgerEntry,
)
from app.schemas.common import DashboardOut, DueItemOut, PnLOut
from app.services import due_dates, exporter

router = APIRouter()


def _compliance_score(pending: int, confirmed: int, anomalies: int, ready_filings: int) -> int:
    """Heuristic 0-100 compliance health score (FR-009)."""
    total = pending + confirmed
    score = 100
    if total:
        score -= int(40 * pending / total)       # un-reviewed backlog hurts
    score -= min(20, anomalies * 2)              # open anomalies hurt
    score += min(10, ready_filings * 5)          # confirmed filings help
    days = due_dates.days_until_next_due()
    if days is not None and days < 0:
        score -= 25                              # overdue
    return max(0, min(100, score))


@router.get("", response_model=DashboardOut)
async def dashboard(
    ctx: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db)
):
    tid = ctx.tenant_id
    period = due_dates.current_period()
    mm, yyyy = int(period[:2]), int(period[2:])

    pending = await db.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.tenant_id == tid, Invoice.status == STATUS_NEEDS_REVIEW
        )
    )
    confirmed = await db.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.tenant_id == tid, Invoice.status == STATUS_CONFIRMED
        )
    )

    # Period sales / purchases / taxes from confirmed invoices.
    async def _period_sum(direction: str):
        res = await db.execute(
            select(
                func.coalesce(func.sum(Invoice.taxable_value), 0.0),
                func.coalesce(func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst + Invoice.cess),
                              0.0),
            ).where(
                Invoice.tenant_id == tid,
                Invoice.status == STATUS_CONFIRMED,
                Invoice.direction == direction,
                extract("month", Invoice.invoice_date) == mm,
                extract("year", Invoice.invoice_date) == yyyy,
            )
        )
        return res.one()

    sales_taxable, output_tax = await _period_sum(SALES)
    purch_taxable, itc_available = await _period_sum(PURCHASE)

    # ITC claimed = ITC on confirmed purchases (booked). For MVP, available==booked ITC.
    itc_claimed = itc_available
    estimated_liability = round(max(float(output_tax) - float(itc_available), 0), 2)

    # Count open high-severity anomalies on invoices still needing review.
    res = await db.execute(
        select(Invoice.anomalies).where(
            Invoice.tenant_id == tid, Invoice.status == STATUS_NEEDS_REVIEW
        )
    )
    anomaly_count = sum(
        1 for (anoms,) in res.all() for a in (anoms or []) if a.get("severity") == "high"
    )

    ready = await db.scalar(
        select(func.count()).select_from(GSTRFiling).where(
            GSTRFiling.tenant_id == tid, GSTRFiling.status != "draft"
        )
    )

    biz = await db.get(Business, tid)
    due_items = due_dates.upcoming_due_dates(scheme=biz.scheme if biz else "regular")
    nxt = due_dates.next_due()

    # Recent activity from ledger.
    recent_res = await db.execute(
        select(LedgerEntry)
        .where(LedgerEntry.tenant_id == tid)
        .order_by(LedgerEntry.created_at.desc())
        .limit(8)
    )
    recent = [
        {
            "type": e.entry_type,
            "party": e.party_name,
            "amount": e.total_value,
            "date": e.entry_date.isoformat() if e.entry_date else None,
        }
        for e in recent_res.scalars().all()
    ]

    return DashboardOut(
        compliance_score=_compliance_score(pending or 0, confirmed or 0, anomaly_count, ready or 0),
        invoices_pending_review=pending or 0,
        next_due=DueItemOut(**nxt.__dict__) if nxt else None,
        days_to_next_due=nxt.days_remaining if nxt else None,
        estimated_tax_liability=estimated_liability,
        itc_available=round(float(itc_available), 2),
        itc_claimed=round(float(itc_claimed), 2),
        upcoming_due_dates=[DueItemOut(**i.__dict__) for i in due_items],
        sales_this_period=round(float(sales_taxable), 2),
        purchases_this_period=round(float(purch_taxable), 2),
        recent_activity=recent,
    )


@router.get("/pnl", response_model=PnLOut)
async def pnl(
    period: str | None = None,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Simple P&L for a period (FR-005)."""
    period = period or due_dates.current_period()
    mm, yyyy = int(period[:2]), int(period[2:])
    p_from = date(yyyy, mm, 1)
    p_to = date(yyyy + (mm == 12), (mm % 12) + 1, 1)

    res = await db.execute(
        select(LedgerEntry).where(
            LedgerEntry.tenant_id == ctx.tenant_id,
            LedgerEntry.entry_date >= p_from,
            LedgerEntry.entry_date < p_to,
        )
    )
    entries = list(res.scalars().all())
    income = round(sum(e.taxable_value for e in entries if e.sign > 0), 2)
    expense = round(sum(e.taxable_value for e in entries if e.sign < 0), 2)
    output_tax = round(sum(e.tax_amount for e in entries if e.sign > 0), 2)
    itc = round(sum(e.tax_amount for e in entries if e.sign < 0), 2)
    return PnLOut(
        period_from=p_from,
        period_to=p_to,
        total_income=income,
        total_expense=expense,
        net=round(income - expense, 2),
        output_tax=output_tax,
        input_tax_credit=itc,
        net_gst_payable=round(max(output_tax - itc, 0), 2),
    )


@router.get("/register/{direction}.xlsx")
async def export_register(
    direction: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Export the sales or purchase register to Excel (FR-009)."""
    direction = SALES if direction.startswith("sale") else PURCHASE
    res = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == ctx.tenant_id, Invoice.direction == direction)
        .order_by(Invoice.invoice_date.desc())
    )
    invoices = list(res.scalars().all())
    title = "Sales Register" if direction == SALES else "Purchase Register"
    data = exporter.register_xlsx(title, invoices)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={direction}_register.xlsx"},
    )
