"""Iteration 11 — Contracts V2 comprehensive backend tests."""
import os
import time
import uuid
import base64
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
OWNER = ("owner@nedtech.media", "Password123!")


def _login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _hdrs(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def tok():
    return _login(*OWNER)


@pytest.fixture(scope="module")
def other_tok():
    # Register a fresh secondary tenant
    email = f"tester_{uuid.uuid4().hex[:8]}@example.com"
    pw = "TestPass123!"
    r = requests.post(f"{BASE}/auth/register", json={
        "email": email, "password": pw, "name": "Tester", "company_name": "OtherCo"
    })
    assert r.status_code in (200, 201), r.text
    return _login(email, pw)


# --- Templates ---
def test_templates_seeded_8_and_visible(tok):
    r = requests.get(f"{BASE}/contracts/templates", headers=_hdrs(tok))
    assert r.status_code == 200
    tpls = r.json()
    sys_tpls = [t for t in tpls if t.get("is_system")]
    assert len(sys_tpls) == 8, f"Expected 8 system templates, got {len(sys_tpls)}"
    names = {t["name"] for t in sys_tpls}
    assert "Website Development Agreement" in names
    assert "Non-Disclosure Agreement (NDA)" in names


def test_templates_no_duplication_across_tenants(other_tok):
    r = requests.get(f"{BASE}/contracts/templates", headers=_hdrs(other_tok))
    assert r.status_code == 200
    sys_tpls = [t for t in r.json() if t.get("is_system")]
    assert len(sys_tpls) == 8


def test_system_template_cannot_be_deleted(tok):
    r = requests.get(f"{BASE}/contracts/templates", headers=_hdrs(tok))
    sys_tpl = next(t for t in r.json() if t.get("is_system"))
    r = requests.delete(f"{BASE}/contracts/templates/{sys_tpl['id']}", headers=_hdrs(tok))
    assert r.status_code == 400


# --- Client + Contract creation snapshot ---
@pytest.fixture(scope="module")
def client_id(tok):
    payload = {
        "name": "Jane Roe", "company": "TestCo", "contact_person": "Jane Roe",
        "email": "jane@testco.example", "phone": "+15551234567",
        "address": "123 Test St", "vat_number": "VAT-987654"
    }
    r = requests.post(f"{BASE}/clients", json=payload, headers=_hdrs(tok))
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body.get("contact_person") == "Jane Roe"
    assert body.get("vat_number") == "VAT-987654"
    return body["id"]


@pytest.fixture(scope="module")
def contract(tok, client_id):
    body_html = (
        "<h1>Deal</h1><p>For {{company_name}}, contact {{contact_person}}. "
        "Amount: {{contract_amount}}.</p>"
    )
    r = requests.post(f"{BASE}/contracts", json={
        "title": "TEST_Iter11 Contract",
        "client_id": client_id,
        "body_html": body_html,
        "contract_amount": 12500,
        "currency": "USD",
    }, headers=_hdrs(tok))
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["status"] == "draft"
    assert c["version"] == 1
    assert c["verification_id"].startswith("NED-C-")
    snap = c.get("client_snapshot")
    assert snap and snap["company"] == "TestCo" and snap["contact_person"] == "Jane Roe"
    assert snap["vat_number"] == "VAT-987654"
    return c


def test_contract_without_client_null_snapshot(tok):
    r = requests.post(f"{BASE}/contracts", json={
        "title": "TEST_no_client", "body_html": "<p>hi</p>"
    }, headers=_hdrs(tok))
    assert r.status_code == 201
    assert r.json()["client_snapshot"] is None


def test_patch_increments_version_and_versions_endpoint(tok, contract):
    cid = contract["id"]
    r = requests.patch(f"{BASE}/contracts/{cid}", json={
        "title": "TEST_Iter11 Contract v2",
        "body_html": "<p>updated body</p>",
        "client_id": contract.get("client_id"),
    }, headers=_hdrs(tok))
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2

    r = requests.get(f"{BASE}/contracts/{cid}/versions", headers=_hdrs(tok))
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) >= 2
    # newest first
    assert versions[0]["created_at"] >= versions[-1]["created_at"]


def test_restore_version(tok, contract):
    cid = contract["id"]
    versions = requests.get(f"{BASE}/contracts/{cid}/versions", headers=_hdrs(tok)).json()
    # earliest version had original body containing {{company_name}}
    earliest = versions[-1]
    r = requests.post(f"{BASE}/contracts/{cid}/versions/{earliest['id']}/restore",
                      headers=_hdrs(tok))
    assert r.status_code == 200, r.text
    restored = r.json()
    assert "{{company_name}}" in restored["body_html"]


# --- Send / Public flow ---
@pytest.fixture(scope="module")
def sent_contract(tok, contract):
    cid = contract["id"]
    r = requests.post(f"{BASE}/contracts/{cid}/send", headers=_hdrs(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("share_token")
    # Verify status
    r = requests.get(f"{BASE}/contracts/{cid}", headers=_hdrs(tok))
    assert r.json()["status"] == "sent"
    return {"id": cid, "token": data["share_token"]}


def test_public_get_flips_to_viewed_once(sent_contract, tok):
    tok_pub = sent_contract["token"]
    r = requests.get(f"{BASE}/public/contracts/{tok_pub}")
    assert r.status_code == 200
    data = r.json()
    c = data["contract"]
    assert c["status"] == "viewed"
    # Variable substitution
    html = c["rendered_html"]
    assert "TestCo" in html
    assert "Jane Roe" in html
    assert "12,500" in html and "USD" in html
    # Second call keeps viewed (or later) — does not go back to sent
    r2 = requests.get(f"{BASE}/public/contracts/{tok_pub}")
    assert r2.json()["contract"]["status"] in ("viewed", "signed")


def test_public_sign_typed_no_data_required(sent_contract, tok):
    tok_pub = sent_contract["token"]
    r = requests.post(f"{BASE}/public/contracts/{tok_pub}/sign", json={
        "signer_name": "Jane Roe", "signature_type": "typed", "consent": True
    })
    assert r.status_code == 200, r.text
    # Second sign returns 409
    r2 = requests.post(f"{BASE}/public/contracts/{tok_pub}/sign", json={
        "signer_name": "Jane Roe", "signature_type": "typed", "consent": True
    })
    assert r2.status_code == 409


def test_sign_without_consent_returns_400(tok, client_id):
    r = requests.post(f"{BASE}/contracts", json={
        "title": "TEST_noconsent", "client_id": client_id, "body_html": "<p>x</p>",
    }, headers=_hdrs(tok))
    cid = r.json()["id"]
    tok_pub = requests.post(f"{BASE}/contracts/{cid}/send", headers=_hdrs(tok)).json()["share_token"]
    r = requests.post(f"{BASE}/public/contracts/{tok_pub}/sign", json={
        "signer_name": "X", "signature_type": "typed", "consent": False
    })
    assert r.status_code == 400


def test_sign_drawn_requires_signature_data(tok, client_id):
    r = requests.post(f"{BASE}/contracts", json={
        "title": "TEST_drawn", "client_id": client_id, "body_html": "<p>x</p>",
    }, headers=_hdrs(tok))
    cid = r.json()["id"]
    tok_pub = requests.post(f"{BASE}/contracts/{cid}/send", headers=_hdrs(tok)).json()["share_token"]
    # Missing signature_data
    r = requests.post(f"{BASE}/public/contracts/{tok_pub}/sign", json={
        "signer_name": "X", "signature_type": "drawn", "consent": True
    })
    assert r.status_code == 400
    # With data
    png_b64 = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    r = requests.post(f"{BASE}/public/contracts/{tok_pub}/sign", json={
        "signer_name": "X", "signature_type": "drawn", "consent": True,
        "signature_data": png_b64
    })
    assert r.status_code == 200
    # Verify stored
    got = requests.get(f"{BASE}/public/contracts/{tok_pub}").json()["contract"]
    assert got["signature"]["signature_type"] == "drawn"


def test_send_after_signed_400(tok, sent_contract):
    r = requests.post(f"{BASE}/contracts/{sent_contract['id']}/send", headers=_hdrs(tok))
    assert r.status_code == 400


def test_patch_signed_contract_400(tok, sent_contract):
    r = requests.patch(f"{BASE}/contracts/{sent_contract['id']}", json={
        "title": "X", "body_html": "<p>y</p>"
    }, headers=_hdrs(tok))
    assert r.status_code == 400


def test_reject_flow(tok, client_id):
    r = requests.post(f"{BASE}/contracts", json={
        "title": "TEST_reject", "client_id": client_id, "body_html": "<p>x</p>",
    }, headers=_hdrs(tok))
    cid = r.json()["id"]
    tok_pub = requests.post(f"{BASE}/contracts/{cid}/send", headers=_hdrs(tok)).json()["share_token"]
    r = requests.post(f"{BASE}/public/contracts/{tok_pub}/reject", json={
        "reason": "Not interested", "signer_name": "X"
    })
    assert r.status_code == 200
    got = requests.get(f"{BASE}/contracts/{cid}", headers=_hdrs(tok)).json()
    assert got["status"] == "cancelled"
    assert got["rejection"]["reason"] == "Not interested"


def test_reject_after_signed_409(tok, sent_contract):
    r = requests.post(f"{BASE}/public/contracts/{sent_contract['token']}/reject", json={
        "reason": "late"
    })
    assert r.status_code == 409


def test_comment_appends(tok, sent_contract):
    r = requests.post(f"{BASE}/public/contracts/{sent_contract['token']}/comment", json={
        "author": "Client", "body": "Looks great!"
    })
    assert r.status_code == 201
    got = requests.get(f"{BASE}/contracts/{sent_contract['id']}", headers=_hdrs(tok)).json()
    assert any(c["body"] == "Looks great!" for c in got.get("comments", []))


def test_cancel_signed_contract_refused(tok, sent_contract):
    r = requests.post(f"{BASE}/contracts/{sent_contract['id']}/cancel", headers=_hdrs(tok))
    assert r.status_code == 400


def test_pdf_generation(tok, sent_contract):
    r = requests.get(f"{BASE}/contracts/{sent_contract['id']}/pdf", headers=_hdrs(tok))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_public_pdf_no_auth(sent_contract):
    r = requests.get(f"{BASE}/public/contracts/{sent_contract['token']}/pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_dashboard(tok):
    r = requests.get(f"{BASE}/contracts/dashboard", headers=_hdrs(tok))
    assert r.status_code == 200
    d = r.json()
    for key in ("active_count", "signed_count", "pending_signature_count",
                "expiring_count", "total_value", "revenue", "monthly"):
        assert key in d, f"missing {key}"


def test_audit_chronological(tok, sent_contract):
    r = requests.get(f"{BASE}/contracts/{sent_contract['id']}/audit", headers=_hdrs(tok))
    assert r.status_code == 200
    events = r.json()
    evts = [e["event"] for e in events]
    assert "created" in evts and "sent" in evts and "signed" in evts
    times = [e["created_at"] for e in events]
    assert times == sorted(times)


def test_client_timeline_contains_contracts(tok, client_id):
    r = requests.get(f"{BASE}/clients/{client_id}/timeline", headers=_hdrs(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "contracts" in data
    stats = data.get("stats", {})
    assert "contract_count" in stats
    assert "signed_contract_count" in stats


def test_tenant_isolation(tok, other_tok, sent_contract):
    r = requests.get(f"{BASE}/contracts/{sent_contract['id']}", headers=_hdrs(other_tok))
    assert r.status_code == 404


def test_client_fields_new(tok, client_id):
    r = requests.get(f"{BASE}/clients/{client_id}", headers=_hdrs(tok))
    assert r.status_code == 200
    d = r.json()
    assert d.get("contact_person") == "Jane Roe"
    assert d.get("vat_number") == "VAT-987654"
