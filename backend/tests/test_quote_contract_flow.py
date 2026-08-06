"""Iteration 10: Quote Approval → Invoice flow + Contracts & E-Signatures."""
import os
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nedtech-business-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api/v1"

OWNER_EMAIL = "owner@nedtech.media"
OWNER_PW = "Password123!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Quote flow ----------------
@pytest.fixture(scope="module")
def created_quote(h):
    payload = {
        "client_name": "TEST_QuoteClient",
        "issue_date": datetime.now(timezone.utc).date().isoformat(),
        "currency": "USD",
        "items": [{"description": "Consulting", "quantity": 2, "unit_price": 500, "tax_rate": 5}],
        "notes": "TEST quote for iter10",
    }
    r = requests.post(f"{API}/quotes", json=payload, headers=h)
    assert r.status_code in (200, 201), f"create quote failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("id"), data
    assert str(data.get("number", "")).startswith("QUO-"), data
    return data


def test_quote_share_returns_public_url_and_sets_status_sent(h, created_quote):
    qid = created_quote["id"]
    r = requests.post(f"{API}/quotes/{qid}/share", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "share_token" in body and "public_url" in body
    assert "/public/quote/" in body["public_url"]
    # verify status via list
    r2 = requests.get(f"{API}/quotes", headers=h)
    assert r2.status_code == 200
    q = next((x for x in r2.json() if x["id"] == qid), None)
    assert q and q["status"] == "sent"
    # persist token on fixture
    created_quote["share_token"] = body["share_token"]
    created_quote["public_url"] = body["public_url"]


def test_public_get_quote_no_auth(created_quote):
    tok = created_quote["share_token"]
    r = requests.get(f"{API}/public/quotes/{tok}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert "quote" in j and "tenant" in j
    assert j["quote"]["id"] == created_quote["id"]
    assert "totals" in j["quote"]
    # total = 2*500 + 2*500*0.05 = 1050
    assert j["quote"]["totals"]["total"] == 1050.0


def test_public_decision_accept_and_second_call_409(created_quote):
    tok = created_quote["share_token"]
    r = requests.post(f"{API}/public/quotes/{tok}/decision",
                      json={"decision": "accepted", "signer_name": "John Client"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "accepted"
    # Second call
    r2 = requests.post(f"{API}/public/quotes/{tok}/decision",
                       json={"decision": "accepted", "signer_name": "John Client"})
    assert r2.status_code == 409, f"expected 409, got {r2.status_code} {r2.text}"


def test_convert_accepted_quote_to_invoice(h, created_quote):
    qid = created_quote["id"]
    r = requests.post(f"{API}/quotes/{qid}/convert", json={"create_project": False}, headers=h)
    assert r.status_code == 200, r.text
    inv_id = r.json()["invoice_id"]
    assert inv_id
    created_quote["invoice_id"] = inv_id
    # verify invoice exists and references source quote
    r2 = requests.get(f"{API}/invoices/{inv_id}", headers=h)
    assert r2.status_code == 200, r2.text
    inv = r2.json()
    assert inv.get("source_quote_id") == qid
    # verify quote status = converted (via list)
    r3 = requests.get(f"{API}/quotes", headers=h)
    q = next((x for x in r3.json() if x["id"] == qid), None)
    assert q and q["status"] == "converted"


def test_convert_twice_returns_409(h, created_quote):
    qid = created_quote["id"]
    r = requests.post(f"{API}/quotes/{qid}/convert", json={"create_project": False}, headers=h)
    assert r.status_code == 409, r.text


def test_convert_non_accepted_returns_400(h):
    # create fresh draft quote and try to convert
    payload = {
        "client_name": "TEST_DraftQuote",
        "issue_date": datetime.now(timezone.utc).date().isoformat(),
        "currency": "USD",
        "items": [{"description": "X", "quantity": 1, "unit_price": 100, "tax_rate": 0}],
    }
    r = requests.post(f"{API}/quotes", json=payload, headers=h)
    assert r.status_code in (200, 201)
    qid = r.json()["id"]
    r2 = requests.post(f"{API}/quotes/{qid}/convert", json={"create_project": False}, headers=h)
    assert r2.status_code == 400, r2.text
    # cleanup
    requests.delete(f"{API}/quotes/{qid}", headers=h)


# ---------------- Contracts ----------------
@pytest.fixture(scope="module")
def created_template(h):
    r = requests.post(f"{API}/contracts/templates",
                      json={"name": "TEST_TPL", "body_markdown": "# Terms\n\nStandard MSA."},
                      headers=h)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_create_template(created_template):
    assert created_template.get("id")
    assert created_template["name"] == "TEST_TPL"


@pytest.fixture(scope="module")
def created_contract(h):
    payload = {
        "title": "TEST_MSA",
        "client_name": "TEST_ContractClient",
        "body_markdown": "This is the master services agreement body.",
    }
    r = requests.post(f"{API}/contracts", json=payload, headers=h)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["status"] == "draft"
    return data


def test_send_contract_returns_share_token(h, created_contract):
    cid = created_contract["id"]
    r = requests.post(f"{API}/contracts/{cid}/send", headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "share_token" in j and "/public/contract/" in j["public_url"]
    created_contract["share_token"] = j["share_token"]


def test_public_get_contract_no_auth(created_contract):
    tok = created_contract["share_token"]
    r = requests.get(f"{API}/public/contracts/{tok}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contract"]["id"] == created_contract["id"]
    assert "tenant" in body


def test_sign_without_consent_400(created_contract):
    tok = created_contract["share_token"]
    r = requests.post(f"{API}/public/contracts/{tok}/sign",
                      json={"signer_name": "Jane Doe", "consent": False})
    assert r.status_code == 400, r.text


def test_sign_with_consent_ok(created_contract):
    tok = created_contract["share_token"]
    r = requests.post(f"{API}/public/contracts/{tok}/sign",
                      json={"signer_name": "Jane Doe", "consent": True})
    assert r.status_code == 200, r.text
    assert "signed_at" in r.json()


def test_sign_twice_409(created_contract):
    tok = created_contract["share_token"]
    r = requests.post(f"{API}/public/contracts/{tok}/sign",
                      json={"signer_name": "Jane Doe", "consent": True})
    assert r.status_code == 409, r.text


def test_pdf_streams_valid_pdf(h, created_contract):
    cid = created_contract["id"]
    r = requests.get(f"{API}/contracts/{cid}/pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_expired_contract_returns_410_on_sign(h):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    payload = {"title": "TEST_ExpiredContract", "client_name": "X",
               "body_markdown": "expired body", "expires_at": yesterday}
    r = requests.post(f"{API}/contracts", json=payload, headers=h)
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    r2 = requests.post(f"{API}/contracts/{cid}/send", headers=h)
    assert r2.status_code == 200, r2.text
    tok = r2.json()["share_token"]
    r3 = requests.post(f"{API}/public/contracts/{tok}/sign",
                       json={"signer_name": "Late Signer", "consent": True})
    assert r3.status_code == 410, f"expected 410, got {r3.status_code} {r3.text}"
    requests.delete(f"{API}/contracts/{cid}", headers=h)


# ---------------- Tenant isolation ----------------
def test_tenant_isolation_contract(h, created_contract):
    """Create a second tenant user and try to access contract A."""
    email = f"TEST_iso_{int(time.time())}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "Password123!",
                            "name": "Iso User", "company_name": "IsoTenant"})
    if r.status_code not in (200, 201):
        pytest.skip(f"cannot create second tenant: {r.status_code} {r.text}")
    tok = r.json().get("access_token")
    if not tok:
        # login to fetch
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": "Password123!"})
        tok = r2.json().get("access_token")
    h2 = {"Authorization": f"Bearer {tok}"}
    cid = created_contract["id"]
    r3 = requests.get(f"{API}/contracts/{cid}", headers=h2)
    assert r3.status_code in (403, 404), f"tenant isolation broken: {r3.status_code} {r3.text}"


# ---------------- Cleanup ----------------
def test_zz_cleanup(h, created_contract, created_template, created_quote):
    requests.delete(f"{API}/contracts/{created_contract['id']}", headers=h)
    requests.delete(f"{API}/contracts/templates/{created_template['id']}", headers=h)
    requests.delete(f"{API}/quotes/{created_quote['id']}", headers=h)
    if created_quote.get("invoice_id"):
        requests.delete(f"{API}/invoices/{created_quote['invoice_id']}", headers=h)
