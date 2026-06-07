"""User & OTP models (FR-001 Auth & Onboarding)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    mobile: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Global account role; per-business role lives on Membership (RBAC, SRS §3.4).
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    preferred_language: Mapped[str] = mapped_column(String(5), default="en")  # en | hi
    # DPDP consent flags (SRS §3.4)
    consent_data_processing: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_ai_usage: Mapped[bool] = mapped_column(Boolean, default=False)


class OTPChallenge(Base, UUIDMixin, TimestampMixin):
    """Short-lived OTP challenge for mobile login (FR-001)."""

    __tablename__ = "otp_challenges"

    mobile: Mapped[str] = mapped_column(String(15), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
