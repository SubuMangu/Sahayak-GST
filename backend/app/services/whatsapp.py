"""WhatsApp Business API adapter (FR-002 ingestion, FR-010 alerts, §3.2.2 bot).

Outbound: send text / interactive menus. Inbound webhook handling (media → ingestion) lives
in the ``whatsapp`` route. Default provider is ``mock`` (prints messages) so the bot flow can
be exercised without Meta credentials. Switch ``WHATSAPP_PROVIDER`` to ``cloud`` for the Meta
Cloud API.
"""
from __future__ import annotations

import httpx

from app.core.config import settings

_GRAPH = "https://graph.facebook.com/v21.0"


async def send_text(to: str, body: str) -> None:
    provider = settings.WHATSAPP_PROVIDER.lower()
    if provider == "cloud" and settings.WHATSAPP_TOKEN:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"{_GRAPH}/{settings.WHATSAPP_PHONE_ID}/messages",
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": body},
                },
            )
    else:
        print(f"[MOCK WhatsApp] to {to}:\n{body}\n")


async def send_menu(to: str, header: str, options: list[str]) -> None:
    """Quick-reply style menu (welcome message, SRS §3.2.2)."""
    body = header + "\n" + "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
    await send_text(to, body)


WELCOME_OPTIONS = ["Upload Invoice", "Show Dashboard", "Generate Returns", "Help"]
