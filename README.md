# Sahayak GST

**AI-Powered GST & Compliance Automation Platform for Indian Small Businesses, Retailers & MSMEs**

This repository contains the **MVP (v1.0)** implementation of Sahayak GST, built against
`Sahayak_GST_SRS_v1.0`. It is a modular-monolith SaaS that makes GST compliance ~80–90%
automated and affordable for kirana stores, retailers, traders and small CAs.

> ⚖️ **Disclaimer:** Sahayak GST is an *assistive* tool. Final responsibility for accuracy
> and timely filing rests with the taxpayer. We recommend review by a qualified professional
> for complex cases.

---

## What's in this MVP

Mapped to the SRS Functional Requirements (FR-001 … FR-012):

| SRS | Module | Status in MVP |
|-----|--------|---------------|
| FR-001 | Auth & Onboarding (mobile OTP, GSTIN verification, schemes) | ✅ |
| FR-002 | Invoice Ingestion (web upload, WhatsApp webhook, encrypted storage) | ✅ |
| FR-003 | AI Extraction Engine (preprocess → OCR → LLM → rule engine, confidence) | ✅ (pluggable; mock + LLM adapters) |
| FR-004 | Invoice Review & Confirmation (side-by-side, edit, bulk-approve) | ✅ |
| FR-005 | Ledger & Bookkeeping (sales/purchase registers, P&L) | ✅ |
| FR-006 | GSTR Generation (GSTR-1 & GSTR-3B preview + JSON/Excel export) | ✅ |
| FR-007 | Reconciliation (GSTR-2A/2B upload & match) | ✅ |
| FR-008 | E-way Bill (Part-A generation, pluggable NIC adapter) | ✅ (adapter stubbed) |
| FR-009 | Dashboard & Reporting | ✅ |
| FR-010 | Notifications (WhatsApp/Email/SMS, in-app center) | ✅ (pluggable providers) |
| FR-011 | Subscription & Billing (Razorpay, 3 tiers, usage metering) | ✅ (adapter + webhooks) |
| FR-012 | Multilingual (Hindi + English) & Accessibility (PWA) | ✅ |

**External integrations** (WhatsApp Cloud API, PaddleOCR/EasyOCR, Grok/Anthropic LLM,
Razorpay, MSG91, e-waybill NIC) are implemented behind clean **adapter interfaces** with
working **mock providers** so the entire product runs end-to-end locally with **zero paid
keys**. Drop in real credentials via `.env` to switch to live providers.

## Architecture

```
sahayak-gst/
├── backend/        FastAPI (Python 3.11+), SQLAlchemy 2, Pydantic v2, Celery
│   └── app/
│       ├── core/         config, db, security, i18n, deps
│       ├── models/       SQLAlchemy ORM (multi-tenant, tenant_id everywhere)
│       ├── schemas/      Pydantic v2 request/response models
│       ├── services/     domain logic (gstin, gst_calc, extraction, gstr, recon…)
│       ├── api/routes/   auth, businesses, invoices, ledger, compliance, …
│       └── workers/      Celery tasks (OCR/LLM, notifications, reports)
├── frontend/       React 18 + TS + Vite + Tailwind + shadcn-style UI + i18next (PWA)
├── docker-compose.yml   Postgres 16 + Redis + MinIO + backend + worker + frontend
└── .env.example
```

Design follows the SRS "modular monolith" recommendation with clear domain packages and
`tenant_id`-based row-level multi-tenancy.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API:        http://localhost:8000  (Swagger at `/docs`)
- Frontend:   http://localhost:5173
- MinIO:      http://localhost:9001  (console)

## Quick start (local, no Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite+aiosqlite:///./sahayak.db   # SQLite fallback for dev
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Demo login

The mock OTP provider prints the OTP to the backend logs and returns it in the API response
when `ENVIRONMENT=development`. Use any 10-digit Indian mobile number to register/login.

## Tests

```bash
cd backend && pytest          # GSTIN checksum, GST calc, GSTR JSON, due-dates, recon
```

## Data localization & security (SRS §3.4)

- Config defaults to AWS `ap-south-1` (Mumbai) / India-hosted MinIO.
- AES-256 envelope encryption for stored invoice files & sensitive fields.
- JWT access + refresh, OTP, RBAC (Owner / Accountant / Viewer / Admin).
- Audit log for all access to financial records.
- DPDP-aligned consent, data export (JSON/Excel) and account deletion with grace period.

See `docs/` for the API contract notes and assumptions.
