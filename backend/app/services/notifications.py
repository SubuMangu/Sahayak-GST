"""Notification dispatch (FR-010): multi-channel + in-app center.

Persists an in-app Notification and, depending on category/config, fans out to WhatsApp /
email / SMS via the respective provider adapters (mock by default).
"""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification
from app.services import whatsapp


async def send_email(to: str, subject: str, body: str) -> None:
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend" and settings.RESEND_API_KEY:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": settings.EMAIL_FROM, "to": [to],
                      "subject": subject, "html": body},
            )
    else:
        print(f"[MOCK EMAIL] to {to}: {subject}\n{body}")


async def notify(
    db: AsyncSession,
    *,
    tenant_id: str,
    category: str,
    title: str,
    body: str,
    user_id: str | None = None,
    deep_link: str | None = None,
    channels: list[str] | None = None,
    mobile: str | None = None,
    email: str | None = None,
) -> Notification:
    """Create an in-app notification and optionally fan out to external channels."""
    channels = channels or ["in_app"]

    note = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        category=category,
        channel=channels[0],
        title=title,
        body=body,
        deep_link=deep_link,
    )
    db.add(note)
    await db.flush()

    if "whatsapp" in channels and mobile:
        await whatsapp.send_text(mobile, f"*{title}*\n{body}")
    if "email" in channels and email:
        await send_email(email, title, body)

    return note
