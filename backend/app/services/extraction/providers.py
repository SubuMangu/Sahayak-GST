"""Pluggable extraction providers (FR-003 / SRS §4 AI layer).

The pipeline depends only on the ``LLMExtractor`` protocol. Three implementations ship:

  - MockExtractor             : deterministic, offline, zero-cost — powers the demo & tests.
  - OpenAICompatibleExtractor : Grok / Groq / OpenAI-style ``/chat/completions`` JSON mode.
  - AnthropicExtractor        : Claude messages API with tool/JSON output.

Switch via ``EXTRACTION_PROVIDER`` in the environment. Real OCR (PaddleOCR/EasyOCR) plugs in
at ``ocr.py``; here we focus on turning OCR text (or an image) into structured invoice JSON.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta
from typing import Protocol

import httpx

from app.core.config import settings

# Schema we ask the LLM to fill, and that the mock emulates.
EXTRACTION_JSON_SCHEMA = {
    "counterparty_gstin": "string (15-char GSTIN of the other party)",
    "counterparty_name": "string",
    "invoice_no": "string",
    "invoice_date": "YYYY-MM-DD",
    "place_of_supply": "2-digit state code",
    "supplier_state_code": "2-digit state code of supplier",
    "line_items": [
        {
            "description": "string",
            "hsn": "string",
            "qty": "number",
            "rate": "number (unit price)",
            "taxable_value": "number",
            "gst_rate": "number (percent: 0/5/12/18/28)",
        }
    ],
}

_EXTRACTION_PROMPT = (
    "You are an expert at reading Indian GST tax invoices. Extract the fields strictly as "
    "JSON matching this schema (no prose, no markdown):\n"
    f"{json.dumps(EXTRACTION_JSON_SCHEMA, indent=2)}\n"
    "Amounts are in INR. If a field is unreadable, use null. Invoice OCR text follows:\n\n"
)


class LLMExtractor(Protocol):
    def extract(self, *, ocr_text: str, file_hint: str) -> dict: ...


class MockExtractor:
    """Deterministic synthetic extraction so the whole product runs with no API keys.

    Output is seeded by the file hash so re-uploading the same file is stable, while
    different files produce varied, realistic invoices (different parties, HSNs, slabs).
    """

    _SUPPLIERS = [
        ("27AAPFU0939F1ZV", "Maharashtra Traders Pvt Ltd", "27"),
        ("07AAGCS1234M1Z9", "Delhi Wholesale Mart", "07"),
        ("29AAACW1234R1ZV", "Karnataka Distributors", "29"),
        ("24AAAAA0000A1Z8", "Gujarat Supply Co", "24"),
    ]
    _CATALOG = [
        ("Basmati Rice 25kg", "1006", 1200.0, 5),
        ("Refined Sugar 50kg", "1701", 2200.0, 5),
        ("Parle-G Biscuits (carton)", "1905", 850.0, 18),
        ("Toilet Soap (box)", "3401", 640.0, 18),
        ("Cotton T-Shirts (dozen)", "6109", 980.0, 5),
        ("Steel Utensils Set", "7323", 1500.0, 12),
        ("LED Smart TV 32in", "8528", 14500.0, 28),
        ("Notebook Bundle", "4820", 360.0, 18),
    ]

    def extract(self, *, ocr_text: str, file_hint: str) -> dict:
        seed = int(hashlib.sha256(file_hint.encode()).hexdigest(), 16) % (10**8)
        rng = random.Random(seed)

        gstin, name, sstate = rng.choice(self._SUPPLIERS)
        n_lines = rng.randint(1, 4)
        items = []
        for _ in range(n_lines):
            desc, hsn, base, rate = rng.choice(self._CATALOG)
            qty = rng.randint(1, 12)
            unit = round(base * rng.uniform(0.9, 1.1), 2)
            taxable = round(qty * unit, 2)
            items.append(
                {
                    "description": desc,
                    "hsn": hsn,
                    "qty": qty,
                    "rate": unit,
                    "taxable_value": taxable,
                    "gst_rate": rate,
                }
            )

        inv_date = date.today() - timedelta(days=rng.randint(1, 40))
        return {
            "counterparty_gstin": gstin,
            "counterparty_name": name,
            "invoice_no": f"INV-{rng.randint(1000, 9999)}",
            "invoice_date": inv_date.isoformat(),
            "place_of_supply": "07",  # assume buyer in Delhi for the demo persona (Ramesh)
            "supplier_state_code": sstate,
            "line_items": items,
        }


class OpenAICompatibleExtractor:
    """Grok / Groq / OpenAI ``/chat/completions`` with JSON response format."""

    def extract(self, *, ocr_text: str, file_hint: str) -> dict:
        url = f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
        body = {
            "model": settings.LLM_MODEL,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "messages": [{"role": "user", "content": _EXTRACTION_PROMPT + ocr_text}],
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)


class AnthropicExtractor:
    """Anthropic Claude messages API returning structured JSON."""

    def extract(self, *, ocr_text: str, file_hint: str) -> dict:
        url = f"{(settings.LLM_API_BASE or 'https://api.anthropic.com').rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": settings.LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": settings.LLM_MODEL or "claude-haiku-4-5-20251001",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": _EXTRACTION_PROMPT + ocr_text}],
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        # Be tolerant of code fences.
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        return json.loads(text)


def get_extractor() -> LLMExtractor:
    provider = settings.EXTRACTION_PROVIDER.lower()
    if provider == "openai-compatible":
        return OpenAICompatibleExtractor()
    if provider == "anthropic":
        return AnthropicExtractor()
    return MockExtractor()
