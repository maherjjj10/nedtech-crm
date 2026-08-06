"""Iteration 2 backend tests for NED Tech CRM:
Client 360 notes/timeline, Team Invites, Billing (Stripe), Calendar dormant,
Tenant isolation, and Iteration-1 regressions.
"""
import os
import time
import uuid
import requests
import pytest

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # read from /app/frontend/.env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/") + "/api/v1"

BASE = _load_backend_url()

OWNER_EMAIL = "owner@nedtech.media"
OWNER_PASS = "Password123!"
EMAIL_DOMAIN = "nedtech.example.com"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASS})
    if r.status_code != 200:
        # try register
        rr = requests.post(f"{BASE}/auth/register", json={
            "email": OWNER_EMAIL, "password": OWNER_PASS,
            "name": "Owner", "company_name": "NED Tech Media"})
        assert rr.status_code in (200, 201), rr.text
        return rr.json()["access_token"]
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="session")
def owner_me(owner_headers):
    r = requests.get(f"{BASE}/auth/me", headers=owner_headers)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="session")
def tenant_b():
    """Register a second tenant (owner)."""
    email = f"tenantb_{uuid.uuid4().hex[:8]}@nedtech.example.com"
    r = requests.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Password123!",
        "name": "Owner B", "company_name": f"Tenant B {uuid.uuid4().hex[:6]}"})
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot register 2nd tenant: {r.status_code} {r.text}")
    data = r.json()
    return {"token": data["access_token"], "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "email": email, "user": data.get("user"), "tenant": data.get("tenant")}


# ---------- Client 360 notes/timeline ----------
class TestClient360:
    def test_client_notes_crud(self, owner_headers):
        # create client
        cname = f"TEST_client_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/clients", headers=owner_headers,
                          json={"name": cname, "email": "c@x.com"})
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]

        # add note
        r = requests.post(f"{BASE}/clients/{cid}/notes", headers=owner_headers,
                          json={"body": "test note"})
        assert r.status_code == 201, r.text
        note = r.json()
        assert note["body"] == "test note"
        note_id = note["id"]

        # list notes
        r = requests.get(f"{BASE}/clients/{cid}/notes", headers=owner_headers)
        assert r.status_code == 200
        assert any(n["id"] == note_id for n in r.json())

        # delete
        r = requests.delete(f"{BASE}/clients/{cid}/notes/{note_id}", headers=owner_headers)
        assert r.status_code == 204

        r = requests.get(f"{BASE}/clients/{cid}/notes", headers=owner_headers)
        assert not any(n["id"] == note_id for n in r.json())

    def test_client_timeline(self, owner_headers):
        cname = f"TEST_c360_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/clients", headers=owner_headers, json={"name": cname})
        assert r.status_code in (200, 201)
        cid = r.json()["id"]

        # deal with same client_name
        r = requests.post(f"{BASE}/pipeline/deals", headers=owner_headers,
                          json={"title": "Deal1", "client_name": cname, "value": 500, "stage": "won"})
        assert r.status_code in (200, 201), r.text

        # invoice with same client_name
        r = requests.post(f"{BASE}/invoices", headers=owner_headers, json={
            "client_name": cname,
            "items": [{"description": "x", "quantity": 1, "unit_price": 100, "tax_rate": 0}],
        })
        assert r.status_code in (200, 201), r.text

        # add note
        requests.post(f"{BASE}/clients/{cid}/notes", headers=owner_headers, json={"body": "hi"})

        r = requests.get(f"{BASE}/clients/{cid}/timeline", headers=owner_headers)
        assert r.status_code == 200, r.text
        tl = r.json()
        assert tl["client"]["id"] == cid
        assert len(tl["deals"]) >= 1
        assert len(tl["invoices"]) >= 1
        assert len(tl["notes"]) >= 1
        assert "stats" in tl
        assert tl["stats"]["deal_count"] >= 1


# ---------- Team Invites ----------
class TestInvites:
    invite_id = None
    invite_token = None
    invite_email = None

    def test_create_invite(self, owner_headers):
        email = f"invitee_{uuid.uuid4().hex[:6]}@nedtech.example.com"
        r = requests.post(f"{BASE}/tenants/me/invites", headers=owner_headers,
                          json={"email": email, "role": "manager"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert "invite" in data
        inv = data["invite"]
        assert inv["email"] == email
        assert inv["role"] == "manager"
        assert inv.get("token")
        assert inv.get("invite_url")
        # email intentionally not configured
        assert data.get("email", {}).get("sent") is False
        assert data["email"].get("reason") == "email_not_configured"
        TestInvites.invite_id = inv["id"]
        TestInvites.invite_token = inv["token"]
        TestInvites.invite_email = email

    def test_list_invites(self, owner_headers):
        r = requests.get(f"{BASE}/tenants/me/invites", headers=owner_headers)
        assert r.status_code == 200
        assert any(i["id"] == TestInvites.invite_id for i in r.json())

    def test_public_preview_no_auth(self, owner_me):
        r = requests.get(f"{BASE}/invites/{TestInvites.invite_token}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == TestInvites.invite_email
        assert d["role"] == "manager"
        assert d.get("tenant_name")

    def test_duplicate_email_conflict(self, owner_headers):
        # inviting an existing member (owner) → 409
        r = requests.post(f"{BASE}/tenants/me/invites", headers=owner_headers,
                          json={"email": OWNER_EMAIL, "role": "member"})
        assert r.status_code == 409, r.text

    def test_accept_invite_and_tenant_match(self, owner_me):
        token = TestInvites.invite_token
        r = requests.post(f"{BASE}/invites/{token}/accept",
                          json={"password": "Password123!", "name": "Invitee"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("access_token")
        assert d["user"]["tenant_id"] == owner_me["user"]["tenant_id"]

        # already accepted → 404
        r2 = requests.post(f"{BASE}/invites/{token}/accept",
                           json={"password": "x", "name": "y"})
        assert r2.status_code == 404

    def test_revoke_invite(self, owner_headers):
        email = f"revoke_{uuid.uuid4().hex[:6]}@nedtech.example.com"
        r = requests.post(f"{BASE}/tenants/me/invites", headers=owner_headers,
                          json={"email": email, "role": "member"})
        assert r.status_code == 201
        inv = r.json()["invite"]
        rid, tok = inv["id"], inv["token"]

        r = requests.delete(f"{BASE}/tenants/me/invites/{rid}", headers=owner_headers)
        assert r.status_code == 204

        # accepting revoked token → 404
        r = requests.post(f"{BASE}/invites/{tok}/accept",
                         json={"password": "Password123!", "name": "Z"})
        assert r.status_code == 404


# ---------- Billing ----------
class TestBilling:
    session_id = None

    def test_plans(self):
        r = requests.get(f"{BASE}/billing/plans")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("configured") is True
        assert "onboarding_url" in d
        plans = d["plans"]
        assert len(plans) == 3
        for p in plans:
            assert p.get("amount") is not None, f"Plan missing amount: {p}"
            assert p.get("currency")
            assert p.get("interval")
            assert p.get("price_id")

    def test_status_free(self, owner_headers):
        r = requests.get(f"{BASE}/billing/status", headers=owner_headers)
        assert r.status_code == 200
        d = r.json()
        assert d.get("plan") is None
        assert d.get("status") == "free"

    def test_checkout(self, owner_headers):
        r = requests.post(f"{BASE}/billing/checkout", headers=owner_headers, json={
            "lookup_key": "starter_monthly",
            "origin_url": "https://nedtech-business-hub.preview.emergentagent.com",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("checkout_url", "").startswith("https://")
        assert d.get("session_id")
        TestBilling.session_id = d["session_id"]

    def test_session_status_no_auth(self):
        assert TestBilling.session_id
        r = requests.get(f"{BASE}/billing/status/{TestBilling.session_id}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == TestBilling.session_id
        assert "status" in d and "payment_status" in d


# ---------- Calendar dormant ----------
class TestCalendar:
    def test_status(self, owner_headers):
        r = requests.get(f"{BASE}/calendar/status", headers=owner_headers)
        assert r.status_code == 200
        d = r.json()
        assert d.get("configured") is False
        assert d.get("connected") is False

    def test_connect_503(self, owner_headers):
        r = requests.get(f"{BASE}/calendar/connect", headers=owner_headers)
        assert r.status_code == 503, r.text

    def test_sync_task_503(self, owner_headers):
        r = requests.post(f"{BASE}/calendar/sync-task", headers=owner_headers,
                          json={"task_id": "nonexistent"})
        assert r.status_code == 503, r.text


# ---------- Tenant Isolation ----------
class TestTenantIsolation:
    def test_b_cannot_see_a_invites(self, owner_headers, tenant_b):
        # create invite in A
        email = f"iso_{uuid.uuid4().hex[:6]}@nedtech.example.com"
        r = requests.post(f"{BASE}/tenants/me/invites", headers=owner_headers,
                          json={"email": email, "role": "member"})
        assert r.status_code == 201
        a_id = r.json()["invite"]["id"]

        r = requests.get(f"{BASE}/tenants/me/invites", headers=tenant_b["headers"])
        assert r.status_code == 200
        assert not any(i["id"] == a_id for i in r.json())

    def test_b_cannot_see_a_notes(self, owner_headers, tenant_b):
        # Create client in A + note
        cname = f"TEST_iso_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/clients", headers=owner_headers, json={"name": cname})
        assert r.status_code in (200, 201)
        cid = r.json()["id"]
        r = requests.post(f"{BASE}/clients/{cid}/notes", headers=owner_headers, json={"body": "secret"})
        assert r.status_code == 201

        # Tenant B: shouldn't see notes (client not in their tenant)
        r = requests.get(f"{BASE}/clients/{cid}/notes", headers=tenant_b["headers"])
        assert r.status_code == 200
        assert r.json() == []
        # timeline → 404 (client not in tenant)
        r = requests.get(f"{BASE}/clients/{cid}/timeline", headers=tenant_b["headers"])
        assert r.status_code == 404


# ---------- Iteration 1 regression ----------
class TestRegression:
    def test_health(self):
        r = requests.get(f"{BASE}/health")
        assert r.status_code == 200

    def test_auth_me(self, owner_headers):
        r = requests.get(f"{BASE}/auth/me", headers=owner_headers)
        assert r.status_code == 200

    def test_clients_crud(self, owner_headers):
        r = requests.post(f"{BASE}/clients", headers=owner_headers,
                          json={"name": f"TEST_reg_{uuid.uuid4().hex[:6]}"})
        assert r.status_code in (200, 201)
        cid = r.json()["id"]
        r = requests.get(f"{BASE}/clients/{cid}", headers=owner_headers)
        assert r.status_code == 200
        r = requests.delete(f"{BASE}/clients/{cid}", headers=owner_headers)
        assert r.status_code in (200, 204)

    def test_pipeline(self, owner_headers):
        r = requests.get(f"{BASE}/pipeline/stages", headers=owner_headers)
        assert r.status_code == 200
        r = requests.get(f"{BASE}/pipeline/summary", headers=owner_headers)
        assert r.status_code == 200

    def test_tasks(self, owner_headers):
        r = requests.post(f"{BASE}/tasks", headers=owner_headers,
                          json={"title": "TEST_task"})
        assert r.status_code in (200, 201)
        r = requests.get(f"{BASE}/tasks", headers=owner_headers)
        assert r.status_code == 200

    def test_invoice_pdf(self, owner_headers):
        r = requests.post(f"{BASE}/invoices", headers=owner_headers, json={
            "client_name": "TEST_pdf_client",
            "items": [{"description": "x", "quantity": 1, "unit_price": 10, "tax_rate": 0}],
        })
        assert r.status_code in (200, 201)
        iid = r.json()["id"]
        r = requests.get(f"{BASE}/invoices/{iid}/pdf", headers=owner_headers)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")

    def test_expenses(self, owner_headers):
        r = requests.post(f"{BASE}/expenses", headers=owner_headers,
                          json={"category": "misc", "amount": 5})
        assert r.status_code in (200, 201)

    def test_reports_dashboard(self, owner_headers):
        r = requests.get(f"{BASE}/reports/summary", headers=owner_headers)
        assert r.status_code == 200
        r = requests.get(f"{BASE}/dashboard/overview", headers=owner_headers)
        assert r.status_code == 200

    def test_tenants_me(self, owner_headers):
        r = requests.get(f"{BASE}/tenants/me", headers=owner_headers)
        assert r.status_code == 200

    def test_module_toggle(self, owner_headers):
        r = requests.post(f"{BASE}/tenants/me/modules", headers=owner_headers,
                          json={"module": "crm", "enabled": False})
        assert r.status_code == 200
        r = requests.get(f"{BASE}/clients", headers=owner_headers)
        assert r.status_code == 403
        # re-enable
        r = requests.post(f"{BASE}/tenants/me/modules", headers=owner_headers,
                          json={"module": "crm", "enabled": True})
        assert r.status_code == 200
        r = requests.get(f"{BASE}/clients", headers=owner_headers)
        assert r.status_code == 200

    def test_ai_run(self, owner_headers):
        r = requests.get(f"{BASE}/ai/tasks", headers=owner_headers)
        assert r.status_code == 200
        r = requests.post(f"{BASE}/ai/run", headers=owner_headers,
                          json={"task": "chat", "context": "Say hi in 5 words"})
        assert r.status_code == 200, r.text
