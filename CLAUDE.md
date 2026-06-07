# CLAUDE.md — Sahayak GST

AI-powered GST & compliance automation SaaS for Indian MSMEs. Modular-monolith
**FastAPI backend** + **React/TS PWA frontend**. Built to `Sahayak_GST_SRS_v1.0`.

## Layout
- `backend/app/` — `core/` (config, db, security, deps, i18n), `models/`, `schemas/`,
  `services/` (domain logic), `api/routes/`, `workers/` (Celery).
- `frontend/src/` — `pages/`, `components/`, `lib/` (api client, types, format), `locales/`.
- `docs/ASSUMPTIONS.md` — what's real vs mock, SRS traceability. **Read this first.**

## Conventions
- Multi-tenant: every business-data row has `tenant_id`; the active tenant comes from the
  `X-Business-Id` header (falls back to the user's first business).
- All external integrations (OCR, LLM, WhatsApp, SMS, email, Razorpay, e-way, S3) sit behind
  adapters in `services/` with a `mock` provider by default. Don't hardcode a provider —
  add it to config and switch via env.
- GST money math lives in `services/gst_calc.py`; never trust LLM-claimed tax totals — the
  rule engine (`services/extraction/rules.py`) recomputes them.
- Backend uses async SQLAlchemy 2 + Pydantic v2. Frontend uses TanStack Query + Zustand.

## Dev commands
- Backend tests: `cd backend && . .venv/bin/activate && pytest`
- Backend run: `cd backend && uvicorn app.main:app --reload` (SQLite fallback, no services)
- Frontend: `cd frontend && npm run dev` (build check: `npm run build`)
- Full stack: `docker compose up --build`

## Demo login
Dev mode echoes the OTP (fixed `123456`). Any 10-digit mobile starting 6-9 works.
