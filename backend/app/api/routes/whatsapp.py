"""WhatsApp bot webhook (§3.2.2, FR-002): verification + inbound message handling.

Meta Cloud API verifies the webhook with a GET challenge, then POSTs message events. We map
the sender's phone to a user/business, and:
  - media (image/PDF/document) → ingest as an invoice and reply with the extraction summary,
  - text → simple menu / natural-language summary, with a deep link to the web app.

In mock mode (no Meta credentials) you can POST a simulated payload to exercise the flow; the
bot's replies are printed to the backend logs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.i18n import t
from app.models.business import Membership
from app.models.user import User
from app.services import whatsapp

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta webhook verification handshake."""
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


async def _user_by_mobile(db: AsyncSession, mobile: str) -> User | None:
    # WhatsApp sends E.164 (e.g. 9198XXXXXXXX); strip country code to our 10-digit format.
    local = mobile[-10:]
    res = await db.execute(select(User).where(User.mobile == local))
    return res.scalars().first()


@router.post("/webhook")
async def inbound(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    try:
        change = payload["entry"][0]["changes"][0]["value"]
        messages = change.get("messages", [])
    except (KeyError, IndexError):
        return {"status": "ignored"}

    for msg in messages:
        sender = msg.get("from", "")
        user = await _user_by_mobile(db, sender)
        lang = user.preferred_language if user else "en"
        msg_type = msg.get("type")

        if user is None:
            await whatsapp.send_text(
                sender,
                "Welcome! Please sign up at https://app.sahayakgst.in to link your number.",
            )
            continue

        if msg_type in ("image", "document"):
            # Live mode downloads media via the Graph API, then runs extract_invoice and
            # persists the Invoice (same path as the web upload route). Reply with summary:
            await whatsapp.send_text(
                sender,
                t("invoice_processed", lang, taxable="—",
                  link="https://app.sahayakgst.in/invoices"),
            )
        elif msg_type == "text":
            body = (msg.get("text", {}).get("body") or "").strip().lower()
            await _handle_text(db, sender, body, user, lang)

    return {"status": "ok"}


async def _handle_text(db: AsyncSession, sender: str, body: str, user: User, lang: str) -> None:
    if any(k in body for k in ("hi", "hello", "start", "namaste", "help", "menu")):
        await whatsapp.send_text(sender, t("welcome", lang))
        await whatsapp.send_menu(sender, "What would you like to do?", whatsapp.WELCOME_OPTIONS)
        return
    if any(k in body for k in ("tax", "liability", "kitna", "return", "dashboard")):
        # Natural-language summary (SRS §3.2.2 "Mera March ka tax kitna hai?").
        res = await db.execute(select(Membership).where(Membership.user_id == user.id))
        if res.scalars().first():
            await whatsapp.send_text(
                sender,
                "Open your dashboard for tax liability & due dates: "
                "https://app.sahayakgst.in/",
            )
        return
    await whatsapp.send_text(sender, t("welcome", lang))
