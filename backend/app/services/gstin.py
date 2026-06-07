"""GSTIN validation (FR-001, FR-003, FR-005).

A GSTIN is 15 chars: ``SS PPPPPPPPPP E Z C``
  - SS  : 2-digit state code
  - 10  : PAN of the entity
  - E   : entity number (registrations per PAN in a state)
  - Z   : default 'Z'
  - C   : checksum character

This implements the official GSTN checksum (base-36, alternating weights 1/2) so we can
verify a GSTIN offline without any API call. Optionally we can enrich legal name/status via
the GSTN public search API (toggled by ``GSTN_SEARCH_ENABLED``).
"""
from __future__ import annotations

import re

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

_CODE_POINT = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # base-36 alphabet
_FACTOR = [1, 2]

# Indian GST state codes (subset commonly needed; full list in production).
STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
    "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
    "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory",
}


def _checksum_char(first_14: str) -> str:
    total = 0
    for i, ch in enumerate(first_14):
        val = _CODE_POINT.index(ch)
        product = val * _FACTOR[i % 2]
        total += product // 36 + product % 36
    remainder = total % 36
    check_val = (36 - remainder) % 36
    return _CODE_POINT[check_val]


def is_valid_gstin(gstin: str | None) -> bool:
    """Return True iff ``gstin`` is structurally valid AND the checksum matches."""
    if not gstin:
        return False
    gstin = gstin.strip().upper()
    if not GSTIN_REGEX.match(gstin):
        return False
    if gstin[:2] not in STATE_CODES:
        return False
    return _checksum_char(gstin[:14]) == gstin[14]


def state_code(gstin: str) -> str | None:
    gstin = (gstin or "").strip().upper()
    return gstin[:2] if len(gstin) >= 2 else None


def state_name(code: str | None) -> str | None:
    return STATE_CODES.get(code or "")


def pan_from_gstin(gstin: str) -> str | None:
    gstin = (gstin or "").strip().upper()
    return gstin[2:12] if is_valid_gstin(gstin) else None
