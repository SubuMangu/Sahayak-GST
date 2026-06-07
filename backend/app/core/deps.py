"""FastAPI dependencies: current user, tenant resolution, RBAC (SRS §3.4)."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.business import ROLE_OWNER, ROLE_VIEWER, Membership
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = payload["sub"]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


class TenantContext:
    """Resolved tenant + the caller's role within it."""

    def __init__(self, user: User, tenant_id: str, role: str):
        self.user = user
        self.tenant_id = tenant_id
        self.role = role

    @property
    def can_write(self) -> bool:
        return self.role != ROLE_VIEWER


async def get_tenant_context(
    x_business_id: str | None = Header(default=None, alias="X-Business-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Resolve the active business from the ``X-Business-Id`` header and check membership.

    If the header is omitted, fall back to the user's first business (single-business users
    like Ramesh never need to send it; CAs like Priya pass it to switch clients).
    """
    q = select(Membership).where(Membership.user_id == user.id)
    if x_business_id:
        q = q.where(Membership.business_id == x_business_id)
    res = await db.execute(q.order_by(Membership.created_at))
    membership = res.scalars().first()
    if membership is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No accessible business. Complete onboarding or check X-Business-Id.",
        )
    return TenantContext(user=user, tenant_id=membership.business_id, role=membership.role)


def require_write(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    if not ctx.can_write:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is read-only (viewer).")
    return ctx


def require_owner(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    if ctx.role != ROLE_OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner role required.")
    return ctx
