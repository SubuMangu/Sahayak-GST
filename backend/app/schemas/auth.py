from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

MOBILE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian 10-digit mobile


class OTPRequest(BaseModel):
    mobile: str = Field(..., description="10-digit Indian mobile number")

    @field_validator("mobile")
    @classmethod
    def _valid_mobile(cls, v: str) -> str:
        v = v.strip().lstrip("+").removeprefix("91")
        if not MOBILE_RE.match(v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v


class OTPRequestResponse(BaseModel):
    message: str
    # In development only, the OTP is echoed back for frictionless testing.
    dev_otp: str | None = None


class OTPVerify(BaseModel):
    mobile: str
    code: str

    @field_validator("mobile")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lstrip("+").removeprefix("91")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool = False
    onboarding_complete: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    mobile: str
    email: str | None = None
    full_name: str | None = None
    preferred_language: str = "en"
    is_admin: bool = False

    model_config = {"from_attributes": True}
