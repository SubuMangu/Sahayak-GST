"""Celery tasks (SRS §4): async extraction & scheduled reminders.

Tasks bridge the sync Celery world to our async services via ``asyncio.run`` on a fresh
session — kept deliberately small so the real logic stays in the service layer (single source
of truth shared with the HTTP API).
"""
from __future__ import annotations

import asyncio

from app.core.database import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_invoice", bind=True, max_retries=3)
def process_invoice(self, invoice_id: str, file_bytes: bytes, mime: str, file_name: str):
    """Run the extraction pipeline for an uploaded invoice (idempotent, retried)."""
    from app.services.extraction import extract_invoice
    from app.services.invoice_service import apply_extraction, mark_failed

    async def _run():
        async with SessionLocal() as db:
            from app.models.invoice import Invoice

            inv = await db.get(Invoice, invoice_id)
            if inv is None:
                return
            try:
                result = extract_invoice(file_bytes=file_bytes, mime=mime, file_name=file_name)
                apply_extraction(inv, result)
            except Exception as exc:  # noqa: BLE001
                mark_failed(inv, str(exc))
                raise
            await db.commit()

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        # Exponential backoff; dead-letters after max_retries (SRS §3.4 reliability).
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="app.workers.tasks.send_due_reminders")
def send_due_reminders():
    """Daily reminder fan-out (US-03). Mirrors the /notifications/run-due-reminders route."""
    from sqlalchemy import select

    from app.core.i18n import t
    from app.models.business import Business, Membership
    from app.models.user import User
    from app.services import due_dates
    from app.services import notifications as notif_svc

    async def _run():
        reminders = due_dates.reminders_due(days_before=3)
        if not reminders:
            return 0
        sent = 0
        async with SessionLocal() as db:
            res = await db.execute(select(Business).where(Business.is_active.is_(True)))
            for biz in res.scalars().all():
                owner_res = await db.execute(
                    select(User)
                    .join(Membership, Membership.user_id == User.id)
                    .where(Membership.business_id == biz.id)
                    .order_by(Membership.created_at)
                )
                owner = owner_res.scalars().first()
                lang = owner.preferred_language if owner else "en"
                for item in reminders:
                    body = t("filing_due", lang, return_type=item.return_type,
                             period=due_dates.period_label(item.period),
                             date=item.due_date.strftime("%d %b"), days=item.days_remaining)
                    await notif_svc.notify(
                        db, tenant_id=biz.id, category="filing_due",
                        title=f"{item.return_type} due soon", body=body,
                        user_id=owner.id if owner else None,
                        channels=["in_app", "whatsapp"],
                        mobile=owner.mobile if owner else None, deep_link="/returns",
                    )
                    sent += 1
            await db.commit()
        return sent

    return asyncio.run(_run())
