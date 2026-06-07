from __future__ import annotations

from pydantic import BaseModel


class GSTRGenerateRequest(BaseModel):
    return_type: str  # GSTR1 | GSTR3B
    period: str       # MMYYYY


class GSTRFilingOut(BaseModel):
    id: str
    return_type: str
    period: str
    status: str
    summary: dict | None = None
    is_nil: bool = False

    model_config = {"from_attributes": True}


class GSTRConfirmRequest(BaseModel):
    filing_id: str


class ReconRunOut(BaseModel):
    id: str
    source: str
    period: str
    summary: dict | None = None

    model_config = {"from_attributes": True}


class ReconItemOut(BaseModel):
    id: str
    match_status: str
    supplier_gstin: str | None = None
    invoice_no: str | None = None
    tax_diff: float
    books_data: dict | None = None
    portal_data: dict | None = None
    resolution: str | None = None

    model_config = {"from_attributes": True}


class ReconResolveRequest(BaseModel):
    resolution: str  # claimed | reconciled


class EwayBuildRequest(BaseModel):
    invoice_id: str
    vehicle_no: str | None = None
    transporter_id: str | None = None
    distance_km: int = 0
    trans_mode: str = "1"


class EwayBillOut(BaseModel):
    id: str
    invoice_id: str
    ewb_no: str | None = None
    status: str
    part_a: dict | None = None

    model_config = {"from_attributes": True}
