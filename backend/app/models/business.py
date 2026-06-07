"""Business (tenant) & membership models (FR-001, US-06 multi-client CA).

A Business *is* the tenant (``tenant_id`` referenced by all business-data tables). A user
reaches a business through a Membership row carrying their RBAC role — this is what lets a CA
(Priya) manage many client businesses under one login.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# RBAC roles (SRS §3.4)
ROLE_OWNER = "owner"
ROLE_ACCOUNTANT = "accountant"
ROLE_VIEWER = "viewer"
ROLES = {ROLE_OWNER, ROLE_ACCOUNTANT, ROLE_VIEWER}

SCHEME_REGULAR = "regular"
SCHEME_COMPOSITION = "composition"


class Business(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "businesses"

    legal_name: Mapped[str] = mapped_column(String(255))
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), index=True, nullable=True)
    gstin_status: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Active/...
    scheme: Mapped[str] = mapped_column(String(20), default=SCHEME_REGULAR)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)  # 2-digit GST state

    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Bank details are sensitive → stored encrypted (FR-001 "bank for future payouts").
    bank_account_enc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Membership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memberships"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=ROLE_OWNER)
