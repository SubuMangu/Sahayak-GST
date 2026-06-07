"""OTP generation/verification (FR-001) + SMS provider abstraction.

Mock provider returns the OTP in dev so you can log in without a real SMS gateway. Swap
``SMS_PROVIDER=msg91`` (or twilio) with credentials for production delivery.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import OTPChallenge

MAX_ATTEMPTS = 5


def _hash(mobile: str, code: str) -> str:
    return hashlib.sha256(f"{mobile}:{code}:{settings.SECRET_KEY}".encode()).hexdigest()


def _generate_code() -> str:
    # Fixed code in dev for frictionless demo logins; random otherwise.
    if settings.is_dev:
        return "123456"[: settings.OTP_LENGTH]
    upper = 10**settings.OTP_LENGTH
    return str(secrets.randbelow(upper)).zfill(settings.OTP_LENGTH)


async def send_sms(mobile: str, message: str) -> None:
    provider = settings.SMS_PROVIDER.lower()
    if provider == "msg91" and settings.MSG91_AUTH_KEY:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                "https://control.msg91.com/api/v5/flow/",
                headers={"authkey": settings.MSG91_AUTH_KEY},
                json={"template_id": settings.MSG91_TEMPLATE_ID,
                      "recipients": [{"mobiles": f"91{mobile}", "otp": message}]},
            )
    else:
        # Mock: log only (printed by uvicorn).
        print(f"[MOCK SMS] to +91{mobile}: {message}")


async def create_challenge(db: AsyncSession, mobile: str) -> str | None:
    """Create an OTP challenge, send it, and (in dev) return the code for convenience."""
    code = _generate_code()
    challenge = OTPChallenge(
        mobile=mobile,
        code_hash=_hash(mobile, code),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    db.add(challenge)
    await db.flush()
    await send_sms(mobile, f"Your Sahayak GST OTP is {code}. Valid for 5 minutes.")
    return code if settings.is_dev else None


async def verify_challenge(db: AsyncSession, mobile: str, code: str) -> bool:
    res = await db.execute(
        select(OTPChallenge)
        .where(OTPChallenge.mobile == mobile, OTPChallenge.consumed.is_(False))
        .order_by(OTPChallenge.created_at.desc())
    )
    challenge = res.scalars().first()
    if challenge is None:
        return False
    if challenge.attempts >= MAX_ATTEMPTS:
        return False
    # SQLite returns naive datetimes; normalise to UTC before comparing.
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return False

    challenge.attempts += 1
    if _hash(mobile, code) != challenge.code_hash:
        return False
    challenge.consumed = True
    return True
