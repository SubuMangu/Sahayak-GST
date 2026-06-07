# MVP Assumptions, Scope Notes & SRS Traceability

This document records the engineering decisions made while building the Sahayak GST MVP
against `Sahayak_GST_SRS_v1.0`, so reviewers can see exactly what is real, what is stubbed,
and why.

## Guiding principle

Everything in the **MVP scope (SRS §1.4)** is implemented so the product runs **end-to-end
with zero paid API keys**. Where the SRS calls for a third-party/paid integration, we built a
clean **adapter interface** with a working **mock provider** plus the real-provider code path,
toggled by environment variables. This keeps the demo runnable while making productionisation
a config change, not a rewrite.

## What is fully implemented (real logic)

| Area | Notes |
|------|-------|
| GSTIN validation | Official base-36 checksum algorithm, offline (`services/gstin.py`). |
| GST tax engine | Intra/inter-state CGST/SGST/IGST split, rate-wise aggregation, half-up rounding (`services/gst_calc.py`). |
| Rule engine + confidence | HSN→rate cross-check, GSTIN/slab/duplicate/date anomalies, per-field confidence, review gate at 0.85 (`services/extraction/rules.py`). |
| GSTR-1 & GSTR-3B | Portal-shaped JSON (B2B/B2CS grouping, GSTR-3B net liability + ITC) + Excel export (`services/gstr.py`, `services/exporter.py`). |
| Reconciliation | 2A/2B parse + match → matched / mismatch / missing-in-books / missing-in-portal, ITC opportunity vs at-risk (`services/reconciliation.py`). |
| Due dates | GSTR-1 (11th) / GSTR-3B (20th), compliance calendar, 3-day reminders (`services/due_dates.py`). |
| Auth | Mobile OTP, JWT access+refresh, RBAC (owner/accountant/viewer), multi-tenant via `X-Business-Id`. |
| Billing logic | 3-tier plan catalog, feature gating, scan-quota metering. |
| Security | Fernet (AES-256-class) field + file encryption, audit log, input validation, CORS. |
| Frontend | All key screens (SRS §3.2.1), Hindi/English i18n, PWA, accessibility (focus, reduced motion, large tap targets). |

## What is stubbed behind an adapter (swap via `.env`)

| Integration | Mock behaviour | Make it live |
|-------------|----------------|--------------|
| **OCR** (PaddleOCR/EasyOCR) | `ocr.py` returns a descriptor; the mock extractor is seeded by file hash so it produces realistic, deterministic invoices. | Replace `preprocess_and_ocr` body with PaddleOCR. |
| **LLM extraction** | `MockExtractor` generates structured invoices offline. | Set `EXTRACTION_PROVIDER=openai-compatible|anthropic` + keys. |
| **WhatsApp** | Prints messages to logs; webhook verify + inbound parsing implemented. | `WHATSAPP_PROVIDER=cloud` + Meta token/phone id. |
| **SMS/OTP** | OTP printed to logs and (in dev) returned in the API; fixed `123456` in dev. | `SMS_PROVIDER=msg91` + auth key. |
| **Email** | Printed to logs. | `EMAIL_PROVIDER=resend` + key. |
| **Razorpay** | Mock order + immediate `/billing/confirm`. Webhook signature verified when secret set. | `RAZORPAY_PROVIDER=razorpay` + keys. |
| **E-way bill (NIC)** | Generates a synthetic EWB number; Part-A fully built from the invoice. | Wire NIC API call in `eway.generate_eway_bill`. |
| **Object storage** | Encrypted local dir when S3 unset. | Set `S3_*` (AWS ap-south-1 / MinIO). |

## Deliberately out of scope for v1 (per SRS §1.4)

- Full auto-submission to the GST portal (needs GSP/ASP authorization) — v1 is assisted
  export + explicit user confirmation, exactly as the SRS specifies.
- e-Invoicing IRN generation (SRS marks v1.5).
- CA multi-client portal UI (v2) — the **data model and RBAC already support it**
  (`Membership` + `X-Business-Id` switching), but a dedicated bulk CA dashboard is not built.
- Advanced inventory, multi-branch/multi-GSTIN, native mobile apps (PWA-first).

## Implementation choices worth flagging

- **Extraction runs inline** in the upload request for a reliable demo. The identical
  `extract_invoice` call is also exposed as a Celery task (`workers/tasks.py`) for scale;
  flip to async dispatch when OCR/LLM latency warrants it (SRS §3.3 target p95 < 35s).
- **Tables are created on startup** (`init_db`) for zero-config dev. Alembic is in
  `requirements.txt` for production migrations.
- **SQLite fallback** lets `pytest` and `uvicorn --reload` run with no services; Docker
  Compose uses Postgres 16 + Redis + MinIO as the SRS specifies.
- **Authoritative taxes**: line-item taxes are always recomputed by the rule engine, never
  trusted from raw LLM output — the human review gate sits on top (SRS §3.4 "transparent AI").

## Test coverage

`backend/tests/` covers the high-risk logic: GSTIN checksum, GST calculation, due dates,
the rule engine/confidence, GSTR generation, reconciliation, and a full API flow
(OTP → onboard → upload → confirm → dashboard).
