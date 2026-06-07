"""Rule engine / confidence tests (FR-003)."""
from app.services.extraction.pipeline import extract_invoice
from app.services.extraction.rules import validate_extraction


def test_rate_mismatch_flagged():
    raw = {
        "counterparty_gstin": "27AAPFU0939F1ZV",
        "counterparty_name": "Test Supplier",
        "invoice_no": "INV-1",
        "invoice_date": "2026-03-10",
        "place_of_supply": "07",
        "supplier_state_code": "27",
        # Rice (HSN 1006) should be 5%, claim 18% -> mismatch.
        "line_items": [{"description": "Rice", "hsn": "1006", "taxable_value": 1000, "gst_rate": 18}],
    }
    result = validate_extraction(raw)
    codes = {a["code"] for a in result["anomalies"]}
    assert "rate_mismatch" in codes
    assert result["needs_review"] is True


def test_invalid_gstin_flagged():
    raw = {
        "counterparty_gstin": "27AAPFU0939F1ZX",  # bad checksum
        "invoice_no": "INV-2",
        "invoice_date": "2026-03-10",
        "place_of_supply": "07",
        "supplier_state_code": "27",
        "line_items": [{"hsn": "1006", "taxable_value": 1000, "gst_rate": 5}],
    }
    result = validate_extraction(raw)
    assert "invalid_gstin" in {a["code"] for a in result["anomalies"]}


def test_clean_invoice_high_confidence():
    raw = {
        "counterparty_gstin": "27AAPFU0939F1ZV",
        "counterparty_name": "Clean Supplier",
        "invoice_no": "INV-3",
        "invoice_date": "2026-03-10",
        "place_of_supply": "07",
        "supplier_state_code": "27",
        "line_items": [{"description": "Rice", "hsn": "1006", "taxable_value": 1000, "gst_rate": 5}],
    }
    result = validate_extraction(raw)
    # Inter-state (27 supplier, 07 buyer) => IGST 5%.
    assert result["fields"]["igst"] == 50.0
    assert result["overall_confidence"] >= 0.85


def test_mock_pipeline_end_to_end():
    result = extract_invoice(file_bytes=b"dummy-bytes", mime="image/jpeg", file_name="x.jpg")
    assert "fields" in result
    assert result["fields"]["total_value"] >= 0
    assert "dedupe_hash" in result
    # Deterministic for same input.
    again = extract_invoice(file_bytes=b"dummy-bytes", mime="image/jpeg", file_name="x.jpg")
    assert result["dedupe_hash"] == again["dedupe_hash"]
