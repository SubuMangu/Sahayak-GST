# Sahayak GST — User Guide

**GST made simple for Indian small businesses, retailers & MSMEs.**

> **Disclaimer:** Sahayak GST is an assistive tool. Final responsibility for accuracy and timely filing rests with the taxpayer. Consult a qualified professional for complex cases.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Login & Sign Up](#2-login--sign-up)
3. [Business Onboarding](#3-business-onboarding)
4. [Dashboard](#4-dashboard)
5. [Invoices](#5-invoices)
6. [Invoice Review](#6-invoice-review)
7. [Returns Center](#7-returns-center)
8. [Reconciliation](#8-reconciliation)
9. [E-Way Bill](#9-e-way-bill)
10. [Plans & Billing](#10-plans--billing)
11. [Settings](#11-settings)
12. [Language & Accessibility](#12-language--accessibility)
13. [WhatsApp Integration](#13-whatsapp-integration)

---

## 1. Getting Started

### Access

| Mode | URL |
|------|-----|
| Docker (full stack) | http://localhost:5173 |
| Local frontend dev | http://localhost:5173 |
| API (Swagger docs) | http://localhost:8000/docs |

### Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

### Quick start (local, no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite+aiosqlite:///./sahayak.db
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 2. Login & Sign Up

Sahayak GST uses **mobile OTP** — no password required.

1. Open the app and enter your **10-digit Indian mobile number** (starting 6–9).
2. Tap **Send OTP**. The 6-digit code arrives via SMS.
3. Enter the OTP and tap **Verify & Continue**.

**First-time users** are automatically registered and taken to Business Onboarding.  
**Returning users** are taken directly to the Dashboard.

> **Dev / demo mode:** The OTP is printed to the backend logs and displayed on-screen. Use the fixed code `123456` for any number.

---

## 3. Business Onboarding

On first login you must register at least one business.

| Field | Notes |
|-------|-------|
| Business legal name | As registered with GST |
| Trade name | Optional — the name you do business under |
| GSTIN | Validated offline using the official base-36 checksum |
| GST scheme | **Regular** or **Composition** |
| Business address | Physical address |

Tap **Create business**. The app redirects to the Dashboard.

### Switching businesses

If you manage multiple GSTINs, use the **Business Switcher** in the top nav to switch between them. Each business's data is fully isolated.

---

## 4. Dashboard

The Dashboard gives a real-time compliance overview for the current tax period.

| Card | What it shows |
|------|---------------|
| **Compliance Score** | 0–100 score based on pending actions and filing history |
| **Invoices Pending Review** | Invoices the AI extracted but you haven't confirmed yet |
| **Next Filing Due** | Nearest GSTR-1 / GSTR-3B deadline with days remaining |
| **Estimated Tax This Month** | Aggregate GST liability computed by the rule engine |
| **ITC Available** | Input Tax Credit claimable from confirmed purchase invoices |
| **Sales (this period)** | Total taxable sales value |
| **Purchases (this period)** | Total taxable purchase value |

### Compliance Calendar

Lists upcoming GSTR-1 (due 11th) and GSTR-3B (due 20th) deadlines. Overdue items are highlighted.

### Recent Activity

A timeline of the last invoice uploads, confirmations, and return generations.

### Quick upload

Tap **Upload Invoice** (top-right) to go directly to the invoice upload screen.

---

## 5. Invoices

Navigate to **Invoices** in the sidebar.

### Getting sample invoices

If you don't have real invoices handy, use any of these:

| Source | How |
|--------|-----|
| **ClearTax** | [cleartax.in/s/gst-invoice](https://cleartax.in/s/gst-invoice) — free GST invoice sample PDFs |
| **Zoho Invoice** | [zoho.com/invoice/gst-invoice-template](https://www.zoho.com/invoice/gst-invoice-template/) — downloadable PDF/Excel templates |
| **GST Portal** | gst.gov.in → Help → Sample Documents — official sample tax invoices |
| **Web search** | Search "GST tax invoice sample PDF India" — many public examples |

> **Dev / demo mode:** The mock AI extractor ignores file content — it generates a realistic synthetic invoice seeded by the filename. Upload any image or PDF with a different filename each time to get varied invoices. No real OCR or API keys needed.

### Upload an invoice

1. Tap **Upload Invoice**.
2. Drag & drop or click to select a **PDF, JPG, or PNG** file (max 25 MB).
3. Select whether it is a **Sales** or **Purchase** invoice.
4. Tap **Upload**. The AI pipeline runs immediately:
   - Pre-processes and OCRs the document
   - Extracts structured fields (vendor, GSTIN, line items, HSN codes, tax amounts)
   - Validates via the rule engine and flags anomalies
5. Once processing completes, the invoice appears in the list.

### Invoice list

Filter invoices by:
- **Type:** All / Sales / Purchase
- **Status:** Needs Review / Confirmed

Each row shows: Party name, Invoice No, Date, Taxable amount, Total, Status, and AI Confidence score.

---

## 6. Invoice Review

Invoices with an AI confidence score below **0.85** (or with flagged anomalies) land in **Needs Review** status. Always review before confirming.

### Review screen layout

| Panel | Content |
|-------|---------|
| **Left — Original Document** | The uploaded image or PDF rendered as-is |
| **Right — Extracted Details** | Editable fields pre-filled by AI |

### Editable fields

- Party name, GSTIN, invoice number, date
- Line items: description, HSN code, quantity, rate, GST %
- Tax totals are **always recomputed** by the rule engine — they cannot be overridden manually

### Anomalies panel

The rule engine flags:
- HSN code / GST rate mismatches
- Invalid or missing GSTIN
- Duplicate invoice numbers
- Date outside the expected range

Tap **Why this?** next to any field to see the AI's reasoning for its extracted value.

### Confirming an invoice

1. Fix any anomalies (or acknowledge and proceed if you're sure).
2. Tap **Save Changes** to update extracted values.
3. Tap **Confirm & Book** to post the invoice to your ledger.

A confirmed invoice contributes to GST calculations, dashboard KPIs, and GSTR generation.

### Bulk approve

On the Invoices list, select multiple **high-confidence** invoices and tap **Bulk Approve** to confirm them in one step.

---

## 7. Returns Center

Navigate to **Returns** in the sidebar.

### Generate a return

1. Select the **Tax Period** (e.g., May 2026).
2. Choose **GSTR-1** (outward supplies) or **GSTR-3B** (summary + ITC).
3. Tap **Generate**. The system aggregates confirmed invoices into the portal-shaped format.

### Preview and export

| Action | What it does |
|--------|--------------|
| **Preview** | View the structured return data on-screen |
| **Export JSON** | Download GST-portal–compatible JSON |
| **Export Excel** | Download a formatted Excel workbook |

### Filing status

| Status | Meaning |
|--------|---------|
| Draft | Generated, not yet reviewed |
| Ready for Filing | You've reviewed and marked it ready |
| Filed | Manually marked after submitting to the portal |

Tap **Mark Ready to File** after reviewing figures. You are responsible for the final submission on the GST portal.

> **Note:** Auto-submission to the portal requires a GSP/ASP license and is out of scope for v1. Sahayak GST generates the compliant JSON/Excel; you upload it to the portal manually.

---

## 8. Reconciliation

Navigate to **Reconciliation** in the sidebar.

Reconciliation matches your **purchase invoices** (books) against the **GSTR-2A/2B** data downloaded from the GST portal, to identify ITC opportunities and risks.

### Steps

1. Download your **GSTR-2A or 2B JSON** from the GST portal.
2. In Sahayak GST, tap **Upload 2A/2B JSON** and select the file.
3. The system matches invoices automatically.

### Result categories

| Category | What it means |
|----------|---------------|
| **Matched** | Invoice in books matches portal — ITC is safe to claim |
| **Mismatch** | Amounts or fields differ — verify with supplier |
| **Missing in Books** | Supplier filed but you have no invoice — chase the supplier |
| **Missing in Portal** | You have the invoice but supplier hasn't filed — ITC at risk |

### ITC summary

- **ITC Opportunity** — matched purchases where you can claim credit
- **ITC at Risk** — mismatched or missing-in-portal purchases

Use **Claim ITC** to mark a matched item for ITC and **Mark Reconciled** to close it.

---

## 9. E-Way Bill

E-way bill generation is available for sales invoices above the threshold.

The system builds **Part-A** of the e-way bill from the confirmed invoice (consignor/consignee GSTIN, taxable value, HSN, vehicle type). Part-B (vehicle number) must be added at the time of dispatch.

> In MVP the NIC API adapter is stubbed — it returns a synthetic EWB number. Wire `eway.generate_eway_bill` to the live NIC API and set credentials in `.env` to go live.

---

## 10. Plans & Billing

Navigate to **Plans & Billing** in the sidebar.

### Tiers

Three subscription tiers are available. Your current plan and monthly scan quota are shown at the top of the page.

| Plan | Target user |
|------|-------------|
| Starter | Kirana / micro-businesses, low volume |
| Growth | Retailers and traders with moderate invoice volumes |
| Pro | High-volume businesses, CAs managing multiple clients |

### Upgrading

1. Tap **Choose [Plan Name]**.
2. Complete payment via the checkout flow (Razorpay in production; mock checkout in dev).
3. Plan activates immediately and the scan quota resets.

### Scan quota

Each invoice upload consumes one scan from your monthly quota. The dashboard shows scans used this month.

---

## 11. Settings

Navigate to **Settings** in the sidebar.

### Profile

Update your name and email address. Tap **Save**.

### Business details

Edit your business's legal name, trade name, address, and GST scheme. Tap **Save**.

### Language

Switch the UI between **English** and **हिंदी** (Hindi). The change applies immediately across all screens.

### Data & Privacy

| Action | What it does |
|--------|--------------|
| **Export my data** | Downloads your invoices, returns, and account data as JSON/Excel |
| **Delete account** | Initiates account deletion with a 30-day grace period |

Your data is stored in India (AWS Mumbai / MinIO) and is DPDP Act 2023 compliant.

---

## 12. Language & Accessibility

- **Language toggle** in the top nav switches between English and Hindi at any time.
- The app is a **Progressive Web App (PWA)** — install it on your phone from the browser's "Add to Home Screen" option for an app-like experience with offline support.
- Designed for accessibility: large tap targets, keyboard navigation, reduced-motion support.

---

## 13. WhatsApp Integration

Sahayak GST accepts **invoice uploads via WhatsApp**. Send a photo or PDF of an invoice to the registered WhatsApp Business number and the extraction pipeline processes it automatically — no app required.

The system also sends **compliance reminders** via WhatsApp (3 days before GSTR due dates).

> In MVP the WhatsApp Cloud API adapter is stubbed — messages are printed to logs. Set `WHATSAPP_PROVIDER=cloud` and add Meta credentials in `.env` to go live.

---

## Role-Based Access (Multi-user businesses)

Multiple users can be added to a single business with different roles:

| Role | Permissions |
|------|-------------|
| **Owner** | Full access — manage users, settings, billing |
| **Accountant** | Upload invoices, review, generate returns, reconcile |
| **Viewer** | Read-only access to invoices and reports |

Invite additional users from the **Settings → Business Details** screen.

---

## Frequently Asked Questions

**Can Sahayak GST file my returns automatically?**  
No. It generates GSTR-1 / GSTR-3B JSON and Excel in the portal-required format. You upload the file to the GST portal manually. Automated portal submission requires a GSP licence and is planned for a future version.

**Is my financial data secure?**  
Yes. Invoice files and sensitive fields are encrypted with AES-256 before storage. All access to financial records is audit-logged. Data stays in India.

**What happens if the AI extracts wrong values?**  
The rule engine flags anomalies and any field below the confidence threshold is held in "Needs Review". You can edit every field before confirming. Tax totals are always recomputed by the rule engine — never trusted from AI output alone.

**Does it work offline?**  
The PWA caches the shell so the app loads offline. Data operations (upload, review, generate) require an internet connection.

**Which GST schemes are supported?**  
Regular and Composition schemes. Multi-GSTIN support (multiple registrations per business) is planned for v2.
