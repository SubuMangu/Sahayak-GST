"""Business / tenant routes (FR-001 onboarding, US-06 multi-client CA, GSTIN validation)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_context
from app.core.security import encrypt_str
from app.models.billing import Subscription
from app.models.business import ROLE_OWNER, Business, Membership
from app.models.user import User
from app.schemas.business import (
    BusinessCreate,
    BusinessOut,
    BusinessUpdate,
    GSTINValidationResult,
)
from app.services import audit, gstin

router = APIRouter()


@router.get("/validate-gstin/{gstin_value}", response_model=GSTINValidationResult)
async def validate_gstin(gstin_value: str, _: User = Depends(get_current_user)):
    g = gstin_value.strip().upper()
    valid = gstin.is_valid_gstin(g)
    code = gstin.state_code(g)
    return GSTINValidationResult(
        gstin=g,
        valid=valid,
        state_code=code if valid else None,
        state_name=gstin.state_name(code) if valid else None,
    )


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.gstin and not gstin.is_valid_gstin(payload.gstin):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid GSTIN checksum.")

    biz = Business(
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        gstin=(payload.gstin or "").upper() or None,
        scheme=payload.scheme,
        state_code=gstin.state_code(payload.gstin) if payload.gstin else None,
        gstin_status="Active" if payload.gstin else None,
        address=payload.address,
        bank_account_enc=encrypt_str(payload.bank_account),
        bank_ifsc=payload.bank_ifsc,
    )
    db.add(biz)
    await db.flush()

    db.add(Membership(user_id=user.id, business_id=biz.id, role=ROLE_OWNER))
    # Every new tenant starts on the Free plan (FR-011).
    db.add(Subscription(tenant_id=biz.id))
    await audit.log(db, action="business.create", tenant_id=biz.id, user_id=user.id,
                    entity="business", entity_id=biz.id)
    await db.flush()

    out = BusinessOut.model_validate(biz)
    out.role = ROLE_OWNER
    return out


@router.get("", response_model=list[BusinessOut])
async def list_businesses(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Business, Membership.role)
        .join(Membership, Membership.business_id == Business.id)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at)
    )
    out = []
    for biz, role in res.all():
        item = BusinessOut.model_validate(biz)
        item.role = role
        out.append(item)
    return out


@router.get("/current", response_model=BusinessOut)
async def current_business(
    ctx=Depends(get_tenant_context), db: AsyncSession = Depends(get_db)
):
    biz = await db.get(Business, ctx.tenant_id)
    out = BusinessOut.model_validate(biz)
    out.role = ctx.role
    return out


@router.patch("/{business_id}", response_model=BusinessOut)
async def update_business(
    business_id: str,
    payload: BusinessUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id, Membership.business_id == business_id
        )
    )
    membership = res.scalars().first()
    if membership is None or membership.role != ROLE_OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner role required.")

    biz = await db.get(Business, business_id)
    data = payload.model_dump(exclude_unset=True)
    if "gstin" in data and data["gstin"]:
        if not gstin.is_valid_gstin(data["gstin"]):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid GSTIN checksum.")
        biz.gstin = data["gstin"].upper()
        biz.state_code = gstin.state_code(biz.gstin)
    for f in ("legal_name", "trade_name", "scheme", "address", "bank_ifsc"):
        if f in data:
            setattr(biz, f, data[f])
    if "bank_account" in data:
        biz.bank_account_enc = encrypt_str(data["bank_account"])
    db.add(biz)
    await db.flush()

    out = BusinessOut.model_validate(biz)
    out.role = membership.role
    return out
