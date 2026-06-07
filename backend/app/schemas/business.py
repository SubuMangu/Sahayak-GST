from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessCreate(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=255)
    trade_name: str | None = None
    gstin: str | None = None
    scheme: str = "regular"  # regular | composition
    address: str | None = None
    bank_account: str | None = None
    bank_ifsc: str | None = None


class BusinessUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    gstin: str | None = None
    scheme: str | None = None
    address: str | None = None
    bank_account: str | None = None
    bank_ifsc: str | None = None


class BusinessOut(BaseModel):
    id: str
    legal_name: str
    trade_name: str | None = None
    gstin: str | None = None
    gstin_status: str | None = None
    scheme: str
    state_code: str | None = None
    address: str | None = None
    bank_ifsc: str | None = None
    role: str | None = None  # caller's role in this business

    model_config = {"from_attributes": True}


class GSTINValidationResult(BaseModel):
    gstin: str
    valid: bool
    state_code: str | None = None
    state_name: str | None = None
    legal_name: str | None = None
    status: str | None = None
