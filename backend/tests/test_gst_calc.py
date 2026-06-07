"""GST tax computation tests (FR-003/005/006)."""
from app.services.gst_calc import aggregate_invoice, compute_line_tax, is_intra_state


def test_intra_state_splits_cgst_sgst():
    bk = compute_line_tax(1000.0, 18, intra_state=True)
    assert bk.cgst == 90.0
    assert bk.sgst == 90.0
    assert bk.igst == 0.0
    assert bk.total_value == 1180.0


def test_inter_state_uses_igst():
    bk = compute_line_tax(1000.0, 18, intra_state=False)
    assert bk.igst == 180.0
    assert bk.cgst == 0.0
    assert bk.total_tax == 180.0


def test_zero_rate():
    bk = compute_line_tax(500.0, 0, intra_state=True)
    assert bk.total_tax == 0.0
    assert bk.total_value == 500.0


def test_is_intra_state_logic():
    assert is_intra_state("07", "07") is True
    assert is_intra_state("07", "27") is False
    # Unknown defaults to intra-state.
    assert is_intra_state(None, "07") is True


def test_aggregate_rate_wise():
    items = [
        {"taxable_value": 1000.0, "gst_rate": 18},
        {"taxable_value": 2000.0, "gst_rate": 5},
        {"taxable_value": 500.0, "gst_rate": 18},
    ]
    totals = aggregate_invoice(items, supplier_state_code="27", place_of_supply_code="07")
    # Inter-state → IGST only.
    assert totals.breakup.taxable_value == 3500.0
    assert totals.breakup.igst == round(1500 * 0.18 + 2000 * 0.05, 2)
    # Two rate buckets.
    assert set(totals.rate_wise.keys()) == {18, 5}
    assert totals.rate_wise[18].taxable_value == 1500.0
