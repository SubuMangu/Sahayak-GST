"""HSN/SAC master lookup for the rule engine (FR-003, FR-005)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "hsn_master.json"

# Valid GST slabs in India.
GST_SLABS = {0, 3, 5, 12, 18, 28}


@lru_cache
def _master() -> dict[str, dict]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return {str(item["hsn"]): item for item in raw["items"]}


def lookup_rate(hsn: str | None) -> int | None:
    """Return the expected GST rate for an HSN/SAC.

    Matches on the most specific prefix available (HSN codes are hierarchical: 2/4/6/8
    digit). Returns None if unknown.
    """
    if not hsn:
        return None
    hsn = str(hsn).strip()
    master = _master()
    # Try progressively shorter prefixes (8 -> 6 -> 4 -> 2).
    for length in (8, 6, 4, 2):
        key = hsn[:length]
        if key in master:
            return master[key]["gst_rate"]
    return None


def is_known_slab(rate: float | None) -> bool:
    if rate is None:
        return False
    return round(rate) in GST_SLABS
