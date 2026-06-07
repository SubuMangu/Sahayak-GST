"""Deterministic rule engine + confidence scoring (FR-003, FR-005).

After the LLM/mock produces raw fields, this stage:
  - validates GSTIN checksum,
  - cross-checks each line's GST rate against the HSN master,
  - recomputes tax (CGST/SGST/IGST) and cross-checks totals,
  - assigns a per-field confidence (0-1) and collects anomalies,
  - flags low-confidence/anomalous invoices for human review (threshold 0.85, SRS FR-003).

This is what turns a probabilistic extraction into something safe to book.
"""
from __future__ import annotations

from datetime import date

from app.services import gstin as gstin_svc
from app.services import hsn as hsn_svc
from app.services.gst_calc import aggregate_invoice, money

REVIEW_THRESHOLD = 0.85


def _parse_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def validate_extraction(raw: dict) -> dict:
    """Validate & normalise a raw extraction.

    Returns a dict with: ``fields`` (cleaned values incl. computed taxes), ``confidence``
    (per-field 0-1), ``anomalies`` (list of {code,message,severity,field}),
    ``overall_confidence`` and ``needs_review`` (bool).
    """
    anomalies: list[dict] = []
    confidence: dict[str, float] = {}

    counterparty_gstin = (raw.get("counterparty_gstin") or "").strip().upper() or None
    counterparty_name = raw.get("counterparty_name")
    invoice_no = raw.get("invoice_no")
    invoice_date = _parse_date(raw.get("invoice_date"))
    place_of_supply = (raw.get("place_of_supply") or "").strip() or None
    supplier_state_code = (raw.get("supplier_state_code") or "").strip() or None

    # --- GSTIN validation (checksum) ---
    if counterparty_gstin:
        if gstin_svc.is_valid_gstin(counterparty_gstin):
            confidence["counterparty_gstin"] = 0.99
            # Supplier state should match GSTIN prefix.
            if supplier_state_code and gstin_svc.state_code(counterparty_gstin) != supplier_state_code:
                supplier_state_code = gstin_svc.state_code(counterparty_gstin)
        else:
            confidence["counterparty_gstin"] = 0.4
            anomalies.append(
                {
                    "code": "invalid_gstin",
                    "field": "counterparty_gstin",
                    "severity": "high",
                    "message": "GSTIN checksum is invalid — verify the number.",
                }
            )
    else:
        confidence["counterparty_gstin"] = 0.5
        anomalies.append(
            {
                "code": "missing_gstin",
                "field": "counterparty_gstin",
                "severity": "medium",
                "message": "No GSTIN detected (may be a B2C / unregistered supplier).",
            }
        )

    confidence["counterparty_name"] = 0.9 if counterparty_name else 0.5
    confidence["invoice_no"] = 0.95 if invoice_no else 0.4
    if not invoice_no:
        anomalies.append(
            {"code": "missing_invoice_no", "field": "invoice_no", "severity": "high",
             "message": "Invoice number not detected."}
        )
    confidence["invoice_date"] = 0.95 if invoice_date else 0.4
    if invoice_date and invoice_date > date.today():
        anomalies.append(
            {"code": "future_date", "field": "invoice_date", "severity": "medium",
             "message": "Invoice date is in the future."}
        )

    # --- Line items + HSN rate cross-check ---
    clean_items: list[dict] = []
    line_conf: list[float] = []
    for idx, item in enumerate(raw.get("line_items") or []):
        hsn = str(item.get("hsn") or "").strip()
        rate = float(item.get("gst_rate") or 0.0)
        taxable = money(item.get("taxable_value") or 0.0)
        expected = hsn_svc.lookup_rate(hsn)

        item_conf = 0.9
        if not hsn:
            item_conf = 0.55
            anomalies.append(
                {"code": "missing_hsn", "field": f"line_items[{idx}].hsn", "severity": "medium",
                 "message": f"Line {idx + 1}: HSN missing."}
            )
        elif expected is None:
            item_conf = 0.7
            anomalies.append(
                {"code": "unknown_hsn", "field": f"line_items[{idx}].hsn", "severity": "low",
                 "message": f"Line {idx + 1}: HSN {hsn} not in master — rate not verified."}
            )
        elif round(expected) != round(rate):
            item_conf = 0.6
            anomalies.append(
                {"code": "rate_mismatch", "field": f"line_items[{idx}].gst_rate",
                 "severity": "high",
                 "message": (f"Line {idx + 1}: GST {rate}% does not match HSN {hsn} "
                             f"master rate {expected}%.")}
            )
        if not hsn_svc.is_known_slab(rate):
            anomalies.append(
                {"code": "invalid_slab", "field": f"line_items[{idx}].gst_rate",
                 "severity": "high",
                 "message": f"Line {idx + 1}: {rate}% is not a valid GST slab."}
            )
            item_conf = min(item_conf, 0.55)

        clean_items.append(
            {
                "description": item.get("description"),
                "hsn": hsn or None,
                "qty": item.get("qty"),
                "rate": item.get("rate"),
                "taxable_value": taxable,
                "gst_rate": rate,
            }
        )
        line_conf.append(item_conf)

    confidence["line_items"] = round(sum(line_conf) / len(line_conf), 3) if line_conf else 0.4
    if not clean_items:
        anomalies.append(
            {"code": "no_line_items", "field": "line_items", "severity": "high",
             "message": "No line items detected."}
        )

    # --- Tax computation (authoritative; overrides any LLM-claimed totals) ---
    totals = aggregate_invoice(
        clean_items,
        supplier_state_code=supplier_state_code,
        place_of_supply_code=place_of_supply,
    )
    bk = totals.breakup

    fields = {
        "counterparty_gstin": counterparty_gstin,
        "counterparty_name": counterparty_name,
        "invoice_no": invoice_no,
        "invoice_date": invoice_date.isoformat() if invoice_date else None,
        "place_of_supply": place_of_supply,
        "supplier_state_code": supplier_state_code,
        "line_items": clean_items,
        "taxable_value": bk.taxable_value,
        "cgst": bk.cgst,
        "sgst": bk.sgst,
        "igst": bk.igst,
        "cess": bk.cess,
        "total_value": bk.total_value,
        "rate_wise": {str(r): b.as_dict() for r, b in totals.rate_wise.items()},
    }

    # Overall confidence: mean of field confidences, penalised by high-severity anomalies.
    base = sum(confidence.values()) / len(confidence) if confidence else 0.5
    high_sev = sum(1 for a in anomalies if a["severity"] == "high")
    overall = max(0.0, round(base - 0.12 * high_sev, 3))
    needs_review = overall < REVIEW_THRESHOLD or high_sev > 0

    return {
        "fields": fields,
        "confidence": confidence,
        "anomalies": anomalies,
        "overall_confidence": overall,
        "needs_review": needs_review,
    }
