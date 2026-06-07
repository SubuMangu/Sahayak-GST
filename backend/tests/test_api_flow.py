"""End-to-end API flow: OTP login -> onboard -> upload -> confirm -> dashboard -> GSTR."""
import io

import pytest


async def _login(client, mobile="9810012345"):
    r = await client.post("/api/v1/auth/request-otp", json={"mobile": mobile})
    assert r.status_code == 200
    otp = r.json()["dev_otp"]
    assert otp  # dev mode echoes the OTP
    r = await client.post("/api/v1/auth/verify-otp", json={"mobile": mobile, "code": otp})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth(token, business_id=None):
    h = {"Authorization": f"Bearer {token}"}
    if business_id:
        h["X-Business-Id"] = business_id
    return h


@pytest.mark.asyncio
async def test_full_flow(client):
    token = await _login(client)

    # Onboard a business (valid GSTIN).
    r = await client.post(
        "/api/v1/businesses",
        headers=_auth(token),
        json={"legal_name": "Ramesh Kirana Store", "gstin": "07AAGCS1234M1Z9",
              "scheme": "regular"},
    )
    assert r.status_code == 201, r.text
    business_id = r.json()["id"]
    assert r.json()["state_code"] == "07"

    # Upload an invoice (mock extraction runs inline).
    files = {"file": ("invoice.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")}
    r = await client.post(
        "/api/v1/invoices/upload",
        headers=_auth(token, business_id),
        files=files,
        data={"direction": "sales"},
    )
    assert r.status_code == 200, r.text
    invoice_id = r.json()["id"]

    # Confirm it -> ledger entry.
    r = await client.post(
        f"/api/v1/invoices/{invoice_id}/confirm", headers=_auth(token, business_id)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # Dashboard reflects activity.
    r = await client.get("/api/v1/dashboard", headers=_auth(token, business_id))
    assert r.status_code == 200
    body = r.json()
    assert "compliance_score" in body
    assert isinstance(body["upcoming_due_dates"], list)

    # Subscription defaults to free.
    r = await client.get("/api/v1/billing/subscription", headers=_auth(token, business_id))
    assert r.json()["plan"] == "free"


@pytest.mark.asyncio
async def test_invalid_gstin_rejected(client):
    token = await _login(client, mobile="9820011111")
    r = await client.post(
        "/api/v1/businesses",
        headers=_auth(token),
        json={"legal_name": "Bad Co", "gstin": "07AAGCS1234M1Z0"},  # bad checksum
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_blocked(client):
    r = await client.get("/api/v1/dashboard")
    assert r.status_code == 401
