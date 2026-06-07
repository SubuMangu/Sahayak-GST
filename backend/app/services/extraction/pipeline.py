"""End-to-end extraction pipeline orchestration (FR-003).

  preprocess + OCR  ->  LLM/mock structured extraction  ->  rule-engine validation
                                                            (+ duplicate detection)

Returns a single dict the invoice service persists onto the Invoice row.
"""
from __future__ import annotations

import hashlib

from app.services.extraction.ocr import preprocess_and_ocr
from app.services.extraction.providers import get_extractor
from app.services.extraction.rules import validate_extraction


def dedupe_hash(counterparty_gstin: str | None, invoice_no: str | None, total_value) -> str:
    key = f"{(counterparty_gstin or '').upper()}|{(invoice_no or '').strip().upper()}|{total_value}"
    return hashlib.sha256(key.encode()).hexdigest()


def extract_invoice(*, file_bytes: bytes, mime: str, file_name: str) -> dict:
    """Run the full pipeline on a single document."""
    file_hint = file_name or hashlib.sha256(file_bytes).hexdigest()[:16]

    ocr_text = preprocess_and_ocr(file_bytes, mime, file_hint)
    raw = get_extractor().extract(ocr_text=ocr_text, file_hint=file_hint)
    result = validate_extraction(raw)

    f = result["fields"]
    result["dedupe_hash"] = dedupe_hash(
        f.get("counterparty_gstin"), f.get("invoice_no"), f.get("total_value")
    )
    return result
