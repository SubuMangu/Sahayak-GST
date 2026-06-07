"""Compliance routes: GSTR generation/export (FR-006), reconciliation (FR-007), e-way (FR-008)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_tenant_context, require_write
from app.models.business import Business
from app.models.compliance import (
    GSTR_FILED,
    GSTR_READY,
    EwayBill,
    GSTRFiling,
    ReconItem,
    ReconciliationRun,
)
from app.models.invoice import PURCHASE, SALES, STATUS_CONFIRMED, Invoice
from app.schemas.compliance import (
    EwayBuildRequest,
    EwayBillOut,
    GSTRConfirmRequest,
    GSTRFilingOut,
    GSTRGenerateRequest,
    ReconItemOut,
    ReconResolveRequest,
    ReconRunOut,
)
from app.services import audit, billing, eway, exporter
from app.services import gstr as gstr_svc
from app.services import reconciliation as recon_svc
from app.services.invoice_service import get_or_create_subscription

router = APIRouter()


async def _require_feature(db: AsyncSession, ctx: TenantContext, feature: str) -> None:
    sub = await get_or_create_subscription(db, ctx.tenant_id)
    if not billing.plan_allows(sub.plan, feature):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"'{feature}' requires a higher plan. Upgrade to continue.",
        )


async def _confirmed_invoices(
    db: AsyncSession, tenant_id: str, period: str, direction: str | None
) -> list[Invoice]:
    mm, yyyy = int(period[:2]), int(period[2:])
    q = select(Invoice).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status == STATUS_CONFIRMED,
        extract("month", Invoice.invoice_date) == mm,
        extract("year", Invoice.invoice_date) == yyyy,
    )
    if direction:
        q = q.where(Invoice.direction == direction)
    res = await db.execute(q)
    return list(res.scalars().all())


# --------------------------------------------------------------------------- GSTR
@router.post("/gstr/generate", response_model=GSTRFilingOut)
async def generate_gstr(
    payload: GSTRGenerateRequest,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    rtype = payload.return_type.upper()
    if rtype not in ("GSTR1", "GSTR3B"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported return type.")

    biz = await db.get(Business, ctx.tenant_id)
    if rtype == "GSTR1":
        sales = await _confirmed_invoices(db, ctx.tenant_id, payload.period, SALES)
        generated = gstr_svc.generate_gstr1(biz.gstin, payload.period, sales)
    else:
        sales = await _confirmed_invoices(db, ctx.tenant_id, payload.period, SALES)
        purchases = await _confirmed_invoices(db, ctx.tenant_id, payload.period, PURCHASE)
        generated = gstr_svc.generate_gstr3b(biz.gstin, payload.period, sales, purchases)

    # Upsert the draft filing for this period+type.
    res = await db.execute(
        select(GSTRFiling).where(
            GSTRFiling.tenant_id == ctx.tenant_id,
            GSTRFiling.return_type == rtype,
            GSTRFiling.period == payload.period,
        )
    )
    filing = res.scalars().first()
    if filing is None:
        filing = GSTRFiling(tenant_id=ctx.tenant_id, return_type=rtype, period=payload.period)
        db.add(filing)
    if filing.status == GSTR_FILED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Return already marked filed.")

    filing.payload = generated["payload"]
    filing.summary = generated["summary"]
    filing.is_nil = generated["summary"].get("is_nil", False)
    filing.status = "draft"
    await db.flush()
    await audit.log(db, action="gstr.generate", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="gstr_filing", entity_id=filing.id, detail=f"{rtype} {payload.period}")
    return filing


@router.get("/gstr", response_model=list[GSTRFilingOut])
async def list_filings(
    ctx: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(GSTRFiling)
        .where(GSTRFiling.tenant_id == ctx.tenant_id)
        .order_by(GSTRFiling.period.desc(), GSTRFiling.return_type)
    )
    return list(res.scalars().all())


@router.post("/gstr/confirm", response_model=GSTRFilingOut)
async def confirm_filing(
    payload: GSTRConfirmRequest,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """User explicitly confirms before a return is marked 'ready for filing' (FR-006)."""
    filing = await db.get(GSTRFiling, payload.filing_id)
    if filing is None or filing.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filing not found.")
    filing.status = GSTR_READY
    filing.confirmed_by = ctx.user.id
    from datetime import datetime, timezone

    filing.confirmed_at = datetime.now(timezone.utc)
    db.add(filing)
    await audit.log(db, action="gstr.confirm", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="gstr_filing", entity_id=filing.id)
    return filing


def _export_filename(filing: GSTRFiling, ext: str) -> str:
    return f"{filing.return_type}_{filing.period}.{ext}"


@router.get("/gstr/{filing_id}/export.json")
async def export_gstr_json(
    filing_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_feature(db, ctx, "gstr_export")
    filing = await db.get(GSTRFiling, filing_id)
    if filing is None or filing.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filing not found.")
    await audit.log(db, action="gstr.export_json", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="gstr_filing", entity_id=filing.id)
    return Response(
        content=json.dumps(filing.payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={_export_filename(filing, 'json')}"},
    )


@router.get("/gstr/{filing_id}/export.xlsx")
async def export_gstr_xlsx(
    filing_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_feature(db, ctx, "gstr_export")
    filing = await db.get(GSTRFiling, filing_id)
    if filing is None or filing.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filing not found.")

    if filing.return_type == "GSTR1":
        sales = await _confirmed_invoices(db, ctx.tenant_id, filing.period, SALES)
        data = exporter.gstr1_xlsx(filing.summary or {}, sales)
    else:
        data = exporter.gstr3b_xlsx(filing.summary or {})
    await audit.log(db, action="gstr.export_xlsx", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="gstr_filing", entity_id=filing.id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={_export_filename(filing, 'xlsx')}"},
    )


# --------------------------------------------------------------------- Reconciliation
@router.post("/reconcile", response_model=ReconRunOut)
async def reconcile(
    period: str,
    source: str = "2B",
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Upload GSTR-2A/2B JSON and reconcile against booked purchases (FR-007)."""
    await _require_feature(db, ctx, "reconciliation")
    raw = await file.read()
    try:
        portal_records = recon_svc.parse_2b_json(json.loads(raw))
    except (json.JSONDecodeError, AttributeError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid 2A/2B JSON.") from exc

    purchases = await _confirmed_invoices(db, ctx.tenant_id, period, PURCHASE)
    result = recon_svc.reconcile(purchases, portal_records)

    run = ReconciliationRun(
        tenant_id=ctx.tenant_id, source=source.replace("GSTR", "").strip("- "),
        period=period, summary=result.summary,
    )
    db.add(run)
    await db.flush()
    for item in result.items:
        db.add(ReconItem(run_id=run.id, tenant_id=ctx.tenant_id, **item))
    await audit.log(db, action="recon.run", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="recon_run", entity_id=run.id, detail=f"{source} {period}")
    await db.flush()
    return run


@router.get("/reconcile/{run_id}/items", response_model=list[ReconItemOut])
async def recon_items(
    run_id: str,
    match_status: str | None = None,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(ReconItem).where(
        ReconItem.run_id == run_id, ReconItem.tenant_id == ctx.tenant_id
    )
    if match_status:
        q = q.where(ReconItem.match_status == match_status)
    res = await db.execute(q)
    return list(res.scalars().all())


@router.post("/reconcile/items/{item_id}/resolve", response_model=ReconItemOut)
async def resolve_item(
    item_id: str,
    payload: ReconResolveRequest,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ReconItem, item_id)
    if item is None or item.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    item.resolution = payload.resolution
    db.add(item)
    return item


# ------------------------------------------------------------------------- E-way bill
@router.post("/eway", response_model=EwayBillOut)
async def create_eway(
    payload: EwayBuildRequest,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Generate an e-way bill Part-A from a confirmed sale invoice (FR-008)."""
    await _require_feature(db, ctx, "eway_bill")
    inv = await db.get(Invoice, payload.invoice_id)
    if inv is None or inv.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found.")
    if inv.status != STATUS_CONFIRMED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Confirm the invoice first.")

    biz = await db.get(Business, ctx.tenant_id)
    part_a = eway.build_part_a(
        inv, biz.gstin,
        transport={
            "vehicle_no": payload.vehicle_no,
            "transporter_id": payload.transporter_id,
            "distance_km": payload.distance_km,
            "trans_mode": payload.trans_mode,
        },
    )
    generated = eway.generate_eway_bill(part_a)
    ewb = EwayBill(
        tenant_id=ctx.tenant_id, invoice_id=inv.id, ewb_no=generated["ewb_no"],
        status=generated["status"], part_a=part_a,
        valid_until=generated["valid_until"], raw_response=generated["raw_response"],
    )
    db.add(ewb)
    await db.flush()
    await audit.log(db, action="eway.generate", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="eway_bill", entity_id=ewb.id)
    return ewb
