"""GSTR generation + reconciliation tests (FR-006/007)."""
from datetime import date
from types import SimpleNamespace

from app.services.gstr import generate_gstr1, generate_gstr3b
from app.services.reconciliation import parse_2b_json, reconcile


def _inv(**kw):
    base = dict(
        counterparty_gstin="27AAPFU0939F1ZV", counterparty_name="Supplier",
        invoice_no="INV-1", invoice_date=date(2026, 3, 10), place_of_supply="07",
        taxable_value=1000.0, cgst=0.0, sgst=0.0, igst=180.0, cess=0.0, total_value=1180.0,
        line_items=[{"hsn": "1006", "taxable_value": 1000.0, "gst_rate": 18}],
        direction="sales",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_gstr1_b2b_grouping():
    sales = [_inv(invoice_no="S1"), _inv(invoice_no="S2")]
    out = generate_gstr1("07ABCDE1234F1Z5", "032026", sales)
    assert out["payload"]["fp"] == "032026"
    assert len(out["payload"]["b2b"]) == 1  # same counterparty
    assert out["summary"]["b2b_invoices"] == 2
    assert out["summary"]["total_taxable_value"] == 2000.0


def test_gstr1_b2c_when_no_gstin():
    sales = [_inv(counterparty_gstin=None, igst=180.0)]
    out = generate_gstr1("07ABCDE1234F1Z5", "032026", sales)
    assert out["payload"]["b2b"] == []
    assert len(out["payload"]["b2cs"]) >= 1


def test_gstr3b_net_liability():
    sales = [_inv(igst=180.0, taxable_value=1000.0)]
    purchases = [_inv(direction="purchase", igst=90.0, taxable_value=500.0)]
    out = generate_gstr3b("07ABCDE1234F1Z5", "032026", sales, purchases)
    assert out["summary"]["net_tax_payable"]["igst"] == 90.0
    assert out["summary"]["itc_available"] == 90.0


def test_reconcile_matches_and_gaps():
    books = [
        _inv(direction="purchase", invoice_no="P1", igst=180.0),
        _inv(direction="purchase", invoice_no="P2", igst=90.0),
    ]
    portal = [
        {"gstin": "27AAPFU0939F1ZV", "invoice_no": "P1", "igst": 180.0},   # match
        {"gstin": "27AAPFU0939F1ZV", "invoice_no": "P9", "igst": 50.0},    # missing in books
    ]
    result = reconcile(books, portal)
    s = result.summary
    assert s["matched"] == 1
    assert s["missing_in_portal"] == 1   # P2 booked but not in portal
    assert s["missing_in_books"] == 1    # P9 in portal not booked
    assert s["itc_opportunity"] == 50.0


def test_parse_2b_json_portal_shape():
    data = {
        "data": {"docdata": {"b2b": [
            {"ctin": "27AAPFU0939F1ZV", "inv": [
                {"inum": "P1", "itms": [{"itm_det": {"txval": 1000, "iamt": 180}}]}
            ]}
        ]}}
    }
    records = parse_2b_json(data)
    assert records[0]["gstin"] == "27AAPFU0939F1ZV"
    assert records[0]["igst"] == 180.0
