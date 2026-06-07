"""GSTR-1 & GSTR-3B generation (FR-006).

Builds GST-portal-compatible JSON (matching the offline-tool schema closely enough for
upload) plus a human-readable summary. Invoices are grouped:
  - B2B  : counterparty has a valid GSTIN
  - B2CS : no/invalid GSTIN (small B2C, rate-wise consolidated)

GSTR-1  : outward supplies (direction == 'sales') for the period.
GSTR-3B : summary of outward supplies + eligible ITC from inward supplies (purchases).

All tax figures come from the stored, rule-validated invoice rows — never from raw LLM output.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models.invoice import Invoice
from app.services import gstin as gstin_svc
from app.services.gst_calc import money


def _fp(period: str) -> str:
    """Portal financial-period token is MMYYYY (same as our internal period)."""
    return period


def _portal_date(d: date | None) -> str | None:
    return d.strftime("%d-%m-%Y") if d else None


def _is_b2b(inv: Invoice) -> bool:
    return bool(inv.counterparty_gstin and gstin_svc.is_valid_gstin(inv.counterparty_gstin))


def _inv_items(inv: Invoice) -> list[dict]:
    """Rate-wise item details for a single invoice (GSTR-1 ``itms``)."""
    rate_wise: dict[float, dict] = defaultdict(
        lambda: {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0}
    )
    for li in inv.line_items or []:
        rate = float(li.get("gst_rate") or 0.0)
        taxable = float(li.get("taxable_value") or 0.0)
        slot = rate_wise[rate]
        slot["txval"] = money(slot["txval"] + taxable)
    # Distribute invoice-level tax proportionally is overkill here; recompute per slab.
    # Simpler & exact: rebuild from line items using invoice's intra/inter split.
    intra = inv.igst == 0
    items = []
    for num, (rate, agg) in enumerate(sorted(rate_wise.items()), start=1):
        txval = agg["txval"]
        det = {"rt": rate, "txval": txval, "csamt": 0.0}
        if intra:
            det["camt"] = money(txval * rate / 200)
            det["samt"] = money(txval * rate / 200)
        else:
            det["iamt"] = money(txval * rate / 100)
        items.append({"num": num, "itm_det": det})
    return items


def generate_gstr1(gstin: str | None, period: str, sales: list[Invoice]) -> dict:
    """Return (payload, summary) for GSTR-1."""
    b2b_map: dict[str, list[Invoice]] = defaultdict(list)
    b2cs_accum: dict[tuple, dict] = defaultdict(
        lambda: {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0}
    )

    for inv in sales:
        if _is_b2b(inv):
            b2b_map[inv.counterparty_gstin].append(inv)
        else:
            for li in inv.line_items or []:
                rate = float(li.get("gst_rate") or 0.0)
                taxable = float(li.get("taxable_value") or 0.0)
                pos = inv.place_of_supply or "07"
                intra = inv.igst == 0
                key = ("INTRA" if intra else "INTER", pos, rate)
                slot = b2cs_accum[key]
                slot["txval"] = money(slot["txval"] + taxable)
                if intra:
                    slot["camt"] = money(slot["camt"] + taxable * rate / 200)
                    slot["samt"] = money(slot["samt"] + taxable * rate / 200)
                else:
                    slot["iamt"] = money(slot["iamt"] + taxable * rate / 100)

    b2b = []
    for ctin, invs in b2b_map.items():
        b2b.append(
            {
                "ctin": ctin,
                "inv": [
                    {
                        "inum": inv.invoice_no,
                        "idt": _portal_date(inv.invoice_date),
                        "val": inv.total_value,
                        "pos": inv.place_of_supply or "07",
                        "rchrg": "N",
                        "inv_typ": "R",
                        "itms": _inv_items(inv),
                    }
                    for inv in invs
                ],
            }
        )

    b2cs = []
    for (sply_ty, pos, rate), agg in b2cs_accum.items():
        b2cs.append(
            {
                "sply_ty": sply_ty,
                "pos": pos,
                "typ": "OE",
                "rt": rate,
                "txval": agg["txval"],
                "iamt": agg["iamt"],
                "camt": agg["camt"],
                "samt": agg["samt"],
                "csamt": agg["csamt"],
            }
        )

    payload = {"gstin": gstin, "fp": _fp(period), "version": "GST3.0.4", "hash": "hash",
               "b2b": b2b, "b2cs": b2cs}

    total_taxable = money(sum(i.taxable_value for i in sales))
    total_tax = money(sum(i.cgst + i.sgst + i.igst + i.cess for i in sales))
    summary = {
        "return_type": "GSTR1",
        "period": period,
        "total_invoices": len(sales),
        "b2b_invoices": sum(len(v) for v in b2b_map.values()),
        "b2cs_entries": len(b2cs),
        "total_taxable_value": total_taxable,
        "total_tax": total_tax,
        "total_value": money(total_taxable + total_tax),
        "is_nil": len(sales) == 0,
    }
    return {"payload": payload, "summary": summary}


def generate_gstr3b(
    gstin: str | None, period: str, sales: list[Invoice], purchases: list[Invoice]
) -> dict:
    """Return (payload, summary) for GSTR-3B."""
    out_taxable = money(sum(i.taxable_value for i in sales))
    out_iamt = money(sum(i.igst for i in sales))
    out_camt = money(sum(i.cgst for i in sales))
    out_samt = money(sum(i.sgst for i in sales))
    out_csamt = money(sum(i.cess for i in sales))

    itc_iamt = money(sum(i.igst for i in purchases))
    itc_camt = money(sum(i.cgst for i in purchases))
    itc_samt = money(sum(i.sgst for i in purchases))
    itc_csamt = money(sum(i.cess for i in purchases))

    net_igst = money(max(out_iamt - itc_iamt, 0))
    net_cgst = money(max(out_camt - itc_camt, 0))
    net_sgst = money(max(out_samt - itc_samt, 0))
    net_cess = money(max(out_csamt - itc_csamt, 0))

    payload = {
        "gstin": gstin,
        "ret_period": _fp(period),
        "sup_details": {
            "osup_det": {
                "txval": out_taxable,
                "iamt": out_iamt,
                "camt": out_camt,
                "samt": out_samt,
                "csamt": out_csamt,
            },
            "osup_nil_exmp": {"txval": 0.0},
            "isup_rev": {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
        },
        "itc_elg": {
            "itc_avl": [
                {
                    "ty": "OTH",
                    "iamt": itc_iamt,
                    "camt": itc_camt,
                    "samt": itc_samt,
                    "csamt": itc_csamt,
                }
            ],
            "itc_net": {
                "iamt": itc_iamt,
                "camt": itc_camt,
                "samt": itc_samt,
                "csamt": itc_csamt,
            },
        },
    }

    summary = {
        "return_type": "GSTR3B",
        "period": period,
        "outward_taxable_value": out_taxable,
        "outward_tax": money(out_iamt + out_camt + out_samt + out_csamt),
        "itc_available": money(itc_iamt + itc_camt + itc_samt + itc_csamt),
        "net_tax_payable": {
            "igst": net_igst,
            "cgst": net_cgst,
            "sgst": net_sgst,
            "cess": net_cess,
            "total": money(net_igst + net_cgst + net_sgst + net_cess),
        },
        "is_nil": len(sales) == 0 and len(purchases) == 0,
    }
    return {"payload": payload, "summary": summary}
