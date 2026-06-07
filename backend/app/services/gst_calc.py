"""GST tax computation engine (FR-003, FR-005, FR-006).

Core rule: supply is **intra-state** when supplier state == place-of-supply state → split
into CGST + SGST (each = rate/2). Otherwise **inter-state** → IGST (= full rate). All money is
rounded to 2 decimals using banker's-safe half-up rounding consistent with GST portal totals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal


def _money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class TaxBreakup:
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    cess: float = 0.0

    @property
    def total_tax(self) -> float:
        return _money(self.cgst + self.sgst + self.igst + self.cess)

    @property
    def total_value(self) -> float:
        return _money(self.taxable_value + self.total_tax)

    def as_dict(self) -> dict:
        return {
            "taxable_value": self.taxable_value,
            "cgst": self.cgst,
            "sgst": self.sgst,
            "igst": self.igst,
            "cess": self.cess,
            "total_tax": self.total_tax,
            "total_value": self.total_value,
        }


def compute_line_tax(
    taxable_value: float,
    gst_rate: float,
    *,
    intra_state: bool,
    cess_rate: float = 0.0,
) -> TaxBreakup:
    """Compute the tax breakup for a single line given taxable value & GST rate."""
    taxable = _money(taxable_value)
    cess = _money(taxable * cess_rate / 100)
    if intra_state:
        half = _money(taxable * gst_rate / 200)  # rate/2 on each of CGST & SGST
        return TaxBreakup(taxable_value=taxable, cgst=half, sgst=half, cess=cess)
    igst = _money(taxable * gst_rate / 100)
    return TaxBreakup(taxable_value=taxable, igst=igst, cess=cess)


@dataclass
class InvoiceTotals:
    breakup: TaxBreakup = field(default_factory=TaxBreakup)
    rate_wise: dict[float, TaxBreakup] = field(default_factory=dict)


def is_intra_state(supplier_state_code: str | None, place_of_supply_code: str | None) -> bool:
    """Intra-state when both state codes are present and equal."""
    if not supplier_state_code or not place_of_supply_code:
        # Unknown → assume intra-state (most common for kirana); flagged elsewhere.
        return True
    return supplier_state_code == place_of_supply_code


def aggregate_invoice(
    line_items: list[dict],
    *,
    supplier_state_code: str | None,
    place_of_supply_code: str | None,
) -> InvoiceTotals:
    """Aggregate per-line taxes into invoice + rate-wise totals (used for GSTR-1/3B)."""
    intra = is_intra_state(supplier_state_code, place_of_supply_code)
    totals = InvoiceTotals()
    for item in line_items:
        taxable = float(item.get("taxable_value") or 0.0)
        rate = float(item.get("gst_rate") or 0.0)
        cess_rate = float(item.get("cess_rate") or 0.0)
        bk = compute_line_tax(taxable, rate, intra_state=intra, cess_rate=cess_rate)

        totals.breakup.taxable_value = _money(totals.breakup.taxable_value + bk.taxable_value)
        totals.breakup.cgst = _money(totals.breakup.cgst + bk.cgst)
        totals.breakup.sgst = _money(totals.breakup.sgst + bk.sgst)
        totals.breakup.igst = _money(totals.breakup.igst + bk.igst)
        totals.breakup.cess = _money(totals.breakup.cess + bk.cess)

        slot = totals.rate_wise.setdefault(rate, TaxBreakup())
        slot.taxable_value = _money(slot.taxable_value + bk.taxable_value)
        slot.cgst = _money(slot.cgst + bk.cgst)
        slot.sgst = _money(slot.sgst + bk.sgst)
        slot.igst = _money(slot.igst + bk.igst)
        slot.cess = _money(slot.cess + bk.cess)
    return totals


def money(value: float | Decimal) -> float:
    return _money(value)
