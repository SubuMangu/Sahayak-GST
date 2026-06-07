"""Notification routes (FR-010): in-app center + reminder trigger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_tenant_context
from app.core.i18n import t
from app.models.business import Business, Membership
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import MessageOut, NotificationOut
from app.services import due_dates
from app.services import notifications as notif_svc

router = APIRouter()


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(Notification).where(Notification.tenant_id == ctx.tenant_id)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(100)
    res = await db.execute(q)
    return list(res.scalars().all())


@router.post("/{notification_id}/read", response_model=MessageOut)
async def mark_read(
    notification_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Notification, notification_id)
    if note is None or note.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    note.is_read = True
    db.add(note)
    return MessageOut(message="marked read")


@router.post("/read-all", response_model=MessageOut)
async def mark_all_read(
    ctx: TenantContext = Depends(get_tenant_context), db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification)
        .where(Notification.tenant_id == ctx.tenant_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return MessageOut(message="all marked read")


@router.post("/run-due-reminders", response_model=MessageOut)
async def run_due_reminders(db: AsyncSession = Depends(get_db)):
    """Trigger due-date reminders (US-03). Scheduled daily by the Celery beat worker.

    Sends to every business 3 days before each GSTR deadline, in the owner's language,
    via WhatsApp + in-app.
    """
    reminders = due_dates.reminders_due(days_before=3)
    if not reminders:
        return MessageOut(message="No reminders due today.")

    res = await db.execute(select(Business).where(Business.is_active.is_(True)))
    sent = 0
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
                mobile=owner.mobile if owner else None,
                deep_link="/returns",
            )
            sent += 1
    return MessageOut(message=f"Sent {sent} reminder(s).")
