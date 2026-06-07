"""Auth routes (FR-001): mobile OTP login, token refresh, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.business import Membership
from app.models.user import User
from app.schemas.auth import (
    OTPRequest,
    OTPRequestResponse,
    OTPVerify,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.services import otp as otp_svc

router = APIRouter()


@router.post("/request-otp", response_model=OTPRequestResponse)
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)):
    dev_otp = await otp_svc.create_challenge(db, payload.mobile)
    return OTPRequestResponse(message="OTP sent to your mobile number.", dev_otp=dev_otp)


@router.post("/verify-otp", response_model=TokenPair)
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    if not await otp_svc.verify_challenge(db, payload.mobile, payload.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OTP.")

    res = await db.execute(select(User).where(User.mobile == payload.mobile))
    user = res.scalars().first()
    is_new = user is None
    if is_new:
        user = User(mobile=payload.mobile)
        db.add(user)
        await db.flush()

    # Onboarding is complete once the user has at least one business.
    mem = await db.execute(select(Membership).where(Membership.user_id == user.id))
    onboarding_complete = mem.scalars().first() is not None

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        is_new_user=is_new,
        onboarding_complete=onboarding_complete,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise ValueError
        user_id = claims["sub"]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    mem = await db.execute(select(Membership).where(Membership.user_id == user.id))
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        onboarding_complete=mem.scalars().first() is not None,
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    full_name: str | None = None,
    email: str | None = None,
    preferred_language: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if full_name is not None:
        user.full_name = full_name
    if email is not None:
        user.email = email
    if preferred_language in ("en", "hi"):
        user.preferred_language = preferred_language
    db.add(user)
    return user
