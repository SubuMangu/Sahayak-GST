"""Server-side message localization (FR-012): English + Hindi.

Used for AI suggestions, notifications and API error messages that reach the user. The web
UI carries its own i18next catalogs; these are for server-originated text (e.g. WhatsApp
replies, reminder bodies).
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "filing_due": {
        "en": "Your {return_type} for {period} is due on {date} ({days} days left).",
        "hi": "{period} के लिए आपका {return_type} {date} को देय है ({days} दिन शेष)।",
    },
    "review_needed": {
        "en": "{count} invoice(s) need your review before booking.",
        "hi": "{count} इनवॉइस को बुक करने से पहले आपकी समीक्षा चाहिए।",
    },
    "recon_mismatch": {
        "en": "Reconciliation found {count} mismatch(es). Possible ITC impact.",
        "hi": "मिलान में {count} बेमेल मिले। संभावित ITC प्रभाव।",
    },
    "invoice_processed": {
        "en": "Invoice processed. Taxable value ₹{taxable}. Review here: {link}",
        "hi": "इनवॉइस प्रोसेस हो गई। कर योग्य मूल्य ₹{taxable}। यहाँ समीक्षा करें: {link}",
    },
    "welcome": {
        "en": "Welcome to Sahayak GST! Send an invoice photo/PDF to get started.",
        "hi": "सहायक GST में आपका स्वागत है! शुरू करने के लिए इनवॉइस फोटो/PDF भेजें।",
    },
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    lang = lang if lang in ("en", "hi") else "en"
    template = MESSAGES.get(key, {}).get(lang) or MESSAGES.get(key, {}).get("en") or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
