"""Invoice routes (FR-002 ingestion, FR-003 extraction, FR-004 review, FR-005 booking)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import TenantContext, get_tenant_context, require_write
from app.models.billing import UsageRecord
from app.models.invoice import (
    PURCHASE,
    SALES,
    STATUS_CONFIRMED,
    STATUS_NEEDS_REVIEW,
    Invoice,
)
from app.schemas.invoice import (
    BulkApproveRequest,
    InvoiceDetail,
    InvoiceListItem,
    InvoiceUpdate,
    InvoiceUploadResponse,
)
from app.services import audit, billing, storage
from app.services import invoice_service as isvc
from app.services.extraction import extract_invoice

router = APIRouter()

MAX_FILE_BYTES = 25 * 1024 * 1024  # 25MB (SRS §3.3)
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/jpg", "image/webp"}


async def _tenant_invoice(db: AsyncSession, ctx: TenantContext, invoice_id: str) -> Invoice:
    inv = await db.get(Invoice, invoice_id)
    if inv is None or inv.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found.")
    return inv


@router.post("/upload", response_model=InvoiceUploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    direction: str = Form(PURCHASE),
    source: str = Form("web"),
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single invoice file → store encrypted → run extraction pipeline (FR-002/003).

    Extraction runs inline (mock pipeline is fast); for heavy OCR/LLM load the same
    ``extract_invoice`` call is dispatched to the Celery worker (see app/workers).
    """
    if direction not in (SALES, PURCHASE):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid direction.")

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 25MB.")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF/JPEG/PNG allowed."
        )

    # --- Plan quota check (FR-011) ---
    sub = await isvc.get_or_create_subscription(db, ctx.tenant_id)
    if not billing.has_scan_quota(sub.plan, sub.scans_used, sub.topup_scans):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Monthly scan limit reached on the {sub.plan} plan. Upgrade or buy a top-up.",
        )

    file_key = storage.put_invoice_file(ctx.tenant_id, content, file.filename or "invoice")
    inv = Invoice(
        tenant_id=ctx.tenant_id,
        direction=direction,
        source=source,
        file_key=file_key,
        file_mime=file.content_type,
        file_name=file.filename,
    )
    db.add(inv)
    await db.flush()

    try:
        result = extract_invoice(
            file_bytes=content, mime=file.content_type, file_name=file.filename or "invoice"
        )
        # Duplicate detection (FR-003).
        dup = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == ctx.tenant_id,
                Invoice.dedupe_hash == result.get("dedupe_hash"),
                Invoice.id != inv.id,
            )
        )
        if dup.scalars().first() is not None:
            result["anomalies"].append(
                {"code": "duplicate", "field": "invoice_no", "severity": "high",
                 "message": "Possible duplicate of an existing invoice."}
            )
            result["needs_review"] = True
        isvc.apply_extraction(inv, result)
    except Exception as exc:  # noqa: BLE001
        isvc.mark_failed(inv, str(exc))
        await db.flush()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Extraction failed; file stored for retry."
        ) from exc

    sub.scans_used += 1
    sub.invoices_processed += 1
    db.add(UsageRecord(tenant_id=ctx.tenant_id, metric="invoice_scan"))
    await audit.log(db, action="invoice.upload", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="invoice", entity_id=inv.id)

    return InvoiceUploadResponse(
        id=inv.id,
        status=inv.status,
        overall_confidence=inv.overall_confidence,
        needs_review=result["needs_review"],
        message="Invoice processed. Please review and confirm.",
    )


@router.get("", response_model=list[InvoiceListItem])
async def list_invoices(
    direction: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(Invoice).where(Invoice.tenant_id == ctx.tenant_id)
    if direction:
        q = q.where(Invoice.direction == direction)
    if status_filter:
        q = q.where(Invoice.status == status_filter)
    q = q.order_by(Invoice.created_at.desc()).limit(min(limit, 200)).offset(offset)
    res = await db.execute(q)
    return list(res.scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await _tenant_invoice(db, ctx, invoice_id)


@router.get("/{invoice_id}/file")
async def download_invoice_file(
    invoice_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    inv = await _tenant_invoice(db, ctx, invoice_id)
    if not inv.file_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No file stored.")
    data = storage.get_invoice_file(inv.file_key)
    await audit.log(db, action="invoice.view_file", tenant_id=ctx.tenant_id,
                    user_id=ctx.user.id, entity="invoice", entity_id=inv.id)
    return Response(content=data, media_type=inv.file_mime or "application/octet-stream")


@router.patch("/{invoice_id}", response_model=InvoiceDetail)
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Apply user corrections on the review screen, then re-validate taxes (FR-004)."""
    inv = await _tenant_invoice(db, ctx, invoice_id)
    if inv.status == STATUS_CONFIRMED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Confirmed invoices cannot be edited.")

    data = payload.model_dump(exclude_unset=True)
    if payload.line_items is not None:
        inv.line_items = [li.model_dump() for li in payload.line_items]
    for f in ("counterparty_name", "counterparty_gstin", "invoice_no", "place_of_supply",
              "direction", "notes", "needs_accountant_review"):
        if f in data:
            setattr(inv, f, data[f])
    if "invoice_date" in data:
        inv.invoice_date = payload.invoice_date

    isvc.recompute_from_line_items(inv)
    db.add(inv)
    await audit.log(db, action="invoice.edit", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="invoice", entity_id=inv.id)
    return inv


@router.post("/{invoice_id}/confirm", response_model=InvoiceDetail)
async def confirm_invoice(
    invoice_id: str,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a reviewed invoice → post to the ledger (FR-004 → FR-005)."""
    inv = await _tenant_invoice(db, ctx, invoice_id)
    await isvc.confirm_to_ledger(db, inv)
    await audit.log(db, action="invoice.confirm", tenant_id=ctx.tenant_id, user_id=ctx.user.id,
                    entity="invoice", entity_id=inv.id)
    return inv


@router.post("/bulk-approve", response_model=dict)
async def bulk_approve(
    payload: BulkApproveRequest,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    """Bulk-approve low-risk invoices above a confidence threshold (FR-004)."""
    q = select(Invoice).where(
        Invoice.tenant_id == ctx.tenant_id,
        Invoice.status == STATUS_NEEDS_REVIEW,
        Invoice.overall_confidence >= payload.confidence_threshold,
        Invoice.needs_accountant_review.is_(False),
    )
    if payload.invoice_ids:
        q = q.where(Invoice.id.in_(payload.invoice_ids))
    res = await db.execute(q)
    approved = 0
    for inv in res.scalars().all():
        # Don't auto-approve anything with a high-severity anomaly.
        if any(a.get("severity") == "high" for a in (inv.anomalies or [])):
            continue
        await isvc.confirm_to_ledger(db, inv)
        approved += 1
    await audit.log(db, action="invoice.bulk_approve", tenant_id=ctx.tenant_id,
                    user_id=ctx.user.id, detail=f"approved={approved}")
    return {"approved": approved}


@router.delete("/{invoice_id}", response_model=dict)
async def delete_invoice(
    invoice_id: str,
    ctx: TenantContext = Depends(require_write),
    db: AsyncSession = Depends(get_db),
):
    inv = await _tenant_invoice(db, ctx, invoice_id)
    if inv.status == STATUS_CONFIRMED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Cannot delete a confirmed invoice (audit integrity)."
        )
    if inv.file_key and not settings.S3_ENDPOINT_URL:
        storage.delete_invoice_file(inv.file_key)
    await db.delete(inv)
    return {"deleted": True}
