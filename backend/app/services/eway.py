"""E-way bill Part-A generation (FR-008, US-08).

Builds the Part-A payload from a confirmed sale invoice with minimal extra input, then calls
the NIC e-waybill API (or a mock that returns a synthetic EWB number). Inter-state supplies
or invoice value above the threshold require an e-way bill.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.invoice import Invoice

EWB_VALUE_THRESHOLD = 50000.0  # ₹50,000 (common threshold)


def is_eway_required(inv: Invoice) -> bool:
    inter_state = inv.igst > 0
    return inter_state or inv.total_value >= EWB_VALUE_THRESHOLD


def build_part_a(inv: Invoice, supplier_gstin: str | None, *, transport: dict) -> dict:
    """Assemble Part-A from invoice + minimal transport fields the user supplies."""
    return {
        "supplyType": "O",  # outward
        "subSupplyType": "1",  # supply
        "docType": "INV",
        "docNo": inv.invoice_no,
        "docDate": inv.invoice_date.strftime("%d/%m/%Y") if inv.invoice_date else None,
        "fromGstin": supplier_gstin,
        "toGstin": inv.counterparty_gstin or "URP",
        "toTrdName": inv.counterparty_name,
        "fromStateCode": (supplier_gstin or "")[:2] or None,
        "toStateCode": inv.place_of_supply,
        "totalValue": inv.taxable_value,
        "cgstValue": inv.cgst,
        "sgstValue": inv.sgst,
        "igstValue": inv.igst,
        "cessValue": inv.cess,
        "totInvValue": inv.total_value,
        "transporterId": transport.get("transporter_id"),
        "transDistance": transport.get("distance_km", 0),
        "vehicleNo": transport.get("vehicle_no"),
        "transMode": transport.get("trans_mode", "1"),  # 1=road
        "itemList": [
            {
                "productName": li.get("description"),
                "hsnCode": li.get("hsn"),
                "quantity": li.get("qty"),
                "taxableAmount": li.get("taxable_value"),
                "gstRate": li.get("gst_rate"),
            }
            for li in (inv.line_items or [])
        ],
    }


def generate_eway_bill(part_a: dict) -> dict:
    """Call NIC API (live) or mock-generate an EWB number + validity."""
    provider = settings.WHATSAPP_PROVIDER  # placeholder; eway has its own provider in prod
    _ = provider
    # Live integration would POST to e-waybill API with user token here.
    ewb_no = f"{random.randint(1000000000, 9999999999)}"
    valid_until = datetime.now(timezone.utc) + timedelta(days=1)
    return {
        "ewb_no": ewb_no,
        "status": "generated",
        "valid_until": valid_until,
        "raw_response": "mock-eway-response",
    }
