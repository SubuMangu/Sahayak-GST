"""GSTIN checksum validation tests (FR-001/003)."""
from app.services.gstin import is_valid_gstin, pan_from_gstin, state_code, state_name

# Well-known structurally + checksum valid GSTINs.
VALID = [
    "27AAPFU0939F1ZV",
    "29AAACW1234R1ZV",
    "07AAGCS1234M1Z9",
    "24AAAAA0000A1Z8",
]


def test_valid_gstins_pass():
    for g in VALID:
        assert is_valid_gstin(g), g


def test_invalid_checksum_fails():
    # Flip the last (check) digit.
    bad = "27AAPFU0939F1ZX"
    assert not is_valid_gstin(bad)


def test_bad_format_fails():
    assert not is_valid_gstin("INVALID")
    assert not is_valid_gstin("")
    assert not is_valid_gstin(None)
    assert not is_valid_gstin("27AAPFU0939F1Z")  # too short


def test_bad_state_code_fails():
    # 99 is not a valid state code.
    assert not is_valid_gstin("99AAPFU0939F1ZV")


def test_state_helpers():
    assert state_code("07AAGCS1234M1Z9") == "07"
    assert state_name("27") == "Maharashtra"
    assert state_name("07") == "Delhi"


def test_pan_extraction():
    assert pan_from_gstin("27AAPFU0939F1ZV") == "AAPFU0939F"
    assert pan_from_gstin("bad") is None
