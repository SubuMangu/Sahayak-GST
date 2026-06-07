"""GSTR-2A/2B reconciliation engine (FR-007, US-07).

Matches purchase invoices in the user's books against supplier-reported data downloaded
from the GST portal (2A/2B). Classifies each record as:
  - matched              : present in both, tax within tolerance
  - mismatch             : present in both, tax differs beyond tolerance
  - missing_in_books     : in portal but not booked  -> potential ITC the user can claim
  - missing_in_portal    : booked but supplier hasn't reported -> ITC at risk / chase supplier
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.invoice import Invoice
from app.services.gst_calc import money

TAX_TOLERANCE = 1.0  # ₹1 rounding tolerance


def _norm(s) -> str:
    return str(s or "").strip().upper()


def _key(gstin, invoice_no) -> tuple[str, str]:
    return (_norm(gstin), _norm(invoice_no))


@dataclass
class ReconResult:
    items: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _portal_tax(rec: dict) -> float:
    return money(
        float(rec.get("igst", 0) or 0)
        + float(rec.get("cgst", 0) or 0)
        + float(rec.get("sgst", 0) or 0)
        + float(rec.get("cess", 0) or 0)
    )


def reconcile(books: list[Invoice], portal_records: list[dict]) -> ReconResult:
    """Reconcile booked purchases (``books``) with parsed portal rows (``portal_records``).

    Each portal record is a normalised dict:
        {gstin, invoice_no, invoice_date, taxable_value, igst, cgst, sgst, cess}
    """
    book_index = {_key(b.counterparty_gstin, b.invoice_no): b for b in books}
    portal_index = {_key(r.get("gstin"), r.get("invoice_no")): r for r in portal_records}

    items: list[dict] = []
    matched = mismatch = missing_books = missing_portal = 0
    itc_at_risk = itc_opportunity = 0.0

    seen_portal: set = set()

    for key, b in book_index.items():
        book_tax = money(b.cgst + b.sgst + b.igst + b.cess)
        if key in portal_index:
            seen_portal.add(key)
            rec = portal_index[key]
            diff = money(book_tax - _portal_tax(rec))
            if abs(diff) <= TAX_TOLERANCE:
                matched += 1
                status = "matched"
            else:
                mismatch += 1
                status = "mismatch"
            items.append({
                "match_status": status,
                "supplier_gstin": b.counterparty_gstin,
                "invoice_no": b.invoice_no,
                "tax_diff": diff,
                "books_data": {"taxable_value": b.taxable_value, "tax": book_tax},
                "portal_data": {"taxable_value": rec.get("taxable_value"), "tax": _portal_tax(rec)},
            })
        else:
            missing_portal += 1
            itc_at_risk = money(itc_at_risk + book_tax)
            items.append({
                "match_status": "missing_in_portal",
                "supplier_gstin": b.counterparty_gstin,
                "invoice_no": b.invoice_no,
                "tax_diff": book_tax,
                "books_data": {"taxable_value": b.taxable_value, "tax": book_tax},
                "portal_data": None,
            })

    for key, rec in portal_index.items():
        if key in seen_portal:
            continue
        missing_books += 1
        rec_tax = _portal_tax(rec)
        itc_opportunity = money(itc_opportunity + rec_tax)
        items.append({
            "match_status": "missing_in_books",
            "supplier_gstin": rec.get("gstin"),
            "invoice_no": rec.get("invoice_no"),
            "tax_diff": rec_tax,
            "books_data": None,
            "portal_data": {"taxable_value": rec.get("taxable_value"), "tax": rec_tax},
        })

    summary = {
        "total_books": len(book_index),
        "total_portal": len(portal_index),
        "matched": matched,
        "mismatch": mismatch,
        "missing_in_books": missing_books,
        "missing_in_portal": missing_portal,
        "itc_opportunity": itc_opportunity,   # claimable ITC not yet booked
        "itc_at_risk": itc_at_risk,           # booked ITC supplier hasn't reported
    }
    return ReconResult(items=items, summary=summary)


def parse_2b_json(data: dict) -> list[dict]:
    """Parse a GSTR-2B JSON (portal download) into normalised records.

    Tolerant of the common shape ``{"data": {"docdata": {"b2b": [{"ctin", "inv": [...]}]}}}``
    as well as a flat list of records (for simpler uploads / our own exports).
    """
    records: list[dict] = []
    if isinstance(data, list):
        return [_normalise_flat(r) for r in data]

    docdata = (data.get("data") or data).get("docdata") or {}
    for supplier in docdata.get("b2b", []) or []:
        ctin = supplier.get("ctin")
        for inv in supplier.get("inv", []) or []:
            taxable = igst = cgst = sgst = cess = 0.0
            for item in inv.get("items", inv.get("itms", [])) or []:
                det = item.get("itm_det", item)
                taxable += float(det.get("txval", 0) or 0)
                igst += float(det.get("iamt", 0) or 0)
                cgst += float(det.get("camt", 0) or 0)
                sgst += float(det.get("samt", 0) or 0)
                cess += float(det.get("csamt", 0) or 0)
            records.append({
                "gstin": ctin,
                "invoice_no": inv.get("inum"),
                "invoice_date": inv.get("dt") or inv.get("idt"),
                "taxable_value": money(taxable),
                "igst": money(igst), "cgst": money(cgst),
                "sgst": money(sgst), "cess": money(cess),
            })
    return records


def _normalise_flat(r: dict) -> dict:
    return {
        "gstin": r.get("gstin") or r.get("ctin"),
        "invoice_no": r.get("invoice_no") or r.get("inum"),
        "invoice_date": r.get("invoice_date") or r.get("idt"),
        "taxable_value": money(r.get("taxable_value", 0) or 0),
        "igst": money(r.get("igst", 0) or 0),
        "cgst": money(r.get("cgst", 0) or 0),
        "sgst": money(r.get("sgst", 0) or 0),
        "cess": money(r.get("cess", 0) or 0),
    }
