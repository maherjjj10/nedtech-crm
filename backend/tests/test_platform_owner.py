"""Iteration 5: Platform Owner + role hierarchy + impersonation.

Test surface:
  - Seed: maher@tapbyned.com exists as platform_owner (idempotent, unique).
  - Immutability: cannot delete/demote/modify protected owner.
  - Role-grant ceiling: super_admin cannot grant platform_owner or super_admin.
  - Platform endpoints (/tenants, /users, /audit) require platform_role.
  - Impersonation: JWT re-scopes tenant_id and /clients returns TARGET tenant.
  - Impersonation isolation: writes go to target tenant, stop restores original.
  - Regression sanity from iteration 3.
"""
import os
import time
import uuid
import subprocess
import requests
import pytest
from pymongo import MongoClient


def _base():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    assert url, "REACT_APP_BACKEND_URL missing"
    return url.rstrip("/") + "/api/v1"


BASE = _base()

OWNER_EMAIL = "maher@tapbyned.com"
OWNER_PASS = "NedTechOwner2026!"

REG_EMAIL = "owner@nedtech.media"
REG_PASS = "Password123!"


def _mongo():
    return MongoClient("mongodb://localhost:27017").get_database("nedtech_crm")


def _login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    return r


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ------------------------ FIXTURES ------------------------

@pytest.fixture(scope="session")
def maher():
    r = _login(OWNER_EMAIL, OWNER_PASS)
    assert r.status_code == 200, f"platform owner login failed: {r.status_code} {r.text}"
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "tenant": d["tenant"]}


@pytest.fixture(scope="session")
def regular():
    r = _login(REG_EMAIL, REG_PASS)
    if r.status_code != 200:
        rr = requests.post(f"{BASE}/auth/register", json={
            "email": REG_EMAIL, "password": REG_PASS,
            "name": "Owner", "company_name": "NED Tech Media"})
        assert rr.status_code in (200, 201), rr.text
        d = rr.json()
    else:
        d = r.json()
    return {"token": d["access_token"], "user": d["user"], "tenant": d["tenant"]}


@pytest.fixture(scope="session")
def tenant_b():
    email = f"tb_{uuid.uuid4().hex[:8]}@nedtech.example.com"
    r = requests.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Password123!",
        "name": "Owner B", "company_name": f"Tenant B {uuid.uuid4().hex[:6]}"})
    assert r.status_code in (200, 201), r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "tenant": d["tenant"], "email": email}


# ------------------------ SEED ---------------------------

class TestSeed:
    def test_maher_login_and_claims(self, maher):
        u = maher["user"]
        assert u["email"] == OWNER_EMAIL
        assert u.get("platform_role") == "platform_owner"
        assert u.get("protected") is True

    def test_me_surfaces_platform_role(self, maher):
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        u = r.json()["user"]
        assert u.get("platform_role") == "platform_owner"
        assert u.get("protected") is True
        assert not u.get("impersonating_from")

    def test_only_one_platform_owner(self):
        db = _mongo()
        n = db.users.count_documents({"platform_role": "platform_owner"})
        assert n == 1, f"Expected exactly 1 platform_owner, found {n}"

    def test_idempotent_on_restart(self, regular):
        """Restart backend, verify (a) still one platform_owner, (b) not duplicated,
        (c) an artificially injected second owner is demoted to None."""
        db = _mongo()
        # Inject rogue platform_owner: promote the regular user
        reg_id = regular["user"]["id"]
        db.users.update_one({"id": reg_id}, {"$set": {"platform_role": "platform_owner"}})
        assert db.users.count_documents({"platform_role": "platform_owner"}) == 2

        # Restart backend (seed should demote rogue)
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
        # Wait for backend to come back
        for _ in range(30):
            time.sleep(1)
            try:
                if requests.get(f"{BASE}/health", timeout=3).status_code == 200:
                    break
            except Exception:
                pass
        else:
            pytest.fail("Backend did not come back after restart")

        # Verify uniqueness + demotion
        assert db.users.count_documents({"platform_role": "platform_owner"}) == 1
        owner = db.users.find_one({"email": OWNER_EMAIL})
        assert owner and owner.get("platform_role") == "platform_owner"
        assert owner.get("protected") is True
        # And regular user platform_role cleared
        reg = db.users.find_one({"id": reg_id})
        assert reg.get("platform_role") in (None, ""), f"Rogue owner not demoted: {reg.get('platform_role')}"

        # No duplicate maher accounts
        assert db.users.count_documents({"email": OWNER_EMAIL}) == 1


# ------------------------ IMMUTABILITY ---------------------

class TestImmutability:
    def test_cannot_delete_owner(self, maher):
        uid = maher["user"]["id"]
        r = requests.delete(f"{BASE}/platform/users/{uid}", headers=_hdr(maher["token"]))
        assert r.status_code == 403, r.text
        assert "protect" in r.text.lower()

    def test_cannot_patch_owner_role(self, maher):
        uid = maher["user"]["id"]
        # Try to clear platform_role
        r = requests.patch(f"{BASE}/platform/users/{uid}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": ""})
        assert r.status_code == 403, r.text
        # Try to demote tenant role
        r = requests.patch(f"{BASE}/platform/users/{uid}/role",
                           headers=_hdr(maher["token"]),
                           json={"tenant_role": "viewer"})
        assert r.status_code == 403, r.text


# ------------------------ ROLE GRANT CEILING ----------------

class TestRoleCeiling:
    def test_no_one_can_grant_platform_owner(self, maher, regular):
        # Even the owner himself cannot grant platform_owner (unique invariant)
        r = requests.patch(f"{BASE}/platform/users/{regular['user']['id']}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": "platform_owner"})
        assert r.status_code == 403, r.text

    def test_super_admin_cannot_grant_super_admin(self, maher, tenant_b):
        """First promote tenant_b user to super_admin, then have them attempt to grant super_admin."""
        db = _mongo()
        # Promote tenant_b to super_admin via maher
        r = requests.patch(f"{BASE}/platform/users/{tenant_b['user']['id']}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": "super_admin"})
        assert r.status_code == 200, r.text
        assert r.json().get("platform_role") == "super_admin"

        # Re-login tenant_b to get token with platform_role claim
        r = requests.post(f"{BASE}/auth/login", json={"email": tenant_b["email"], "password": "Password123!"})
        assert r.status_code == 200
        sa_tok = r.json()["access_token"]
        assert r.json()["user"]["platform_role"] == "super_admin"

        # As super_admin, attempt to grant super_admin to regular user -> 403
        r = requests.patch(f"{BASE}/platform/users/{tenant_b['user']['id']}/role",
                           headers=_hdr(sa_tok),
                           json={"platform_role": "super_admin"})
        # target is themselves already super_admin; effective_rank should still be checked.
        # Real test: try to grant to someone else
        # find some other user
        other = db.users.find_one({"platform_role": {"$in": [None, ""]}, "email": {"$ne": OWNER_EMAIL}})
        r2 = requests.patch(f"{BASE}/platform/users/{other['id']}/role",
                            headers=_hdr(sa_tok),
                            json={"platform_role": "super_admin"})
        assert r2.status_code == 403, r2.text

        # And cannot grant platform_owner
        r3 = requests.patch(f"{BASE}/platform/users/{other['id']}/role",
                            headers=_hdr(sa_tok),
                            json={"platform_role": "platform_owner"})
        assert r3.status_code == 403, r3.text

        # Cleanup: demote tenant_b back to None so subsequent tests aren't affected
        db.users.update_one({"id": tenant_b["user"]["id"]}, {"$set": {"platform_role": None}})


# ------------------------ PLATFORM ENDPOINTS ----------------

class TestPlatformEndpoints:
    def test_tenants_list(self, maher):
        r = requests.get(f"{BASE}/platform/tenants", headers=_hdr(maher["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        t0 = data[0]
        assert "user_count" in t0
        assert "billing" in t0

    def test_tenant_users(self, maher, tenant_b):
        r = requests.get(f"{BASE}/platform/tenants/{tenant_b['tenant']['id']}/users",
                         headers=_hdr(maher["token"]))
        assert r.status_code == 200
        users = r.json()
        assert any(u["email"] == tenant_b["email"] for u in users)
        assert all("password_hash" not in u for u in users)

    def test_users_search(self, maher):
        r = requests.get(f"{BASE}/platform/users?q=maher", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        arr = r.json()
        assert any(u["email"] == OWNER_EMAIL for u in arr)

    def test_audit(self, maher):
        r = requests.get(f"{BASE}/platform/audit", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_non_platform_forbidden(self, regular):
        for path in ("/platform/tenants", "/platform/users", "/platform/audit"):
            r = requests.get(f"{BASE}{path}", headers=_hdr(regular["token"]))
            assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"


# ------------------------ IMPERSONATION --------------------

class TestImpersonation:
    def test_impersonate_rescope(self, maher, tenant_b):
        target_tid = tenant_b["tenant"]["id"]
        r = requests.post(f"{BASE}/platform/impersonate",
                          headers=_hdr(maher["token"]),
                          json={"tenant_id": target_tid, "reason": "support"})
        assert r.status_code == 200, r.text
        imp_tok = r.json()["access_token"]
        assert imp_tok

        # /me should reflect target tenant + impersonating_from
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(imp_tok))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tenant"]["id"] == target_tid
        assert d["user"].get("impersonating_from") == maher["user"]["id"]

        # audit: impersonation.start present
        r = requests.get(f"{BASE}/platform/audit", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        events = r.json()
        starts = [e for e in events if e.get("action") == "impersonation.start"
                  and e.get("actor_user_id") == maher["user"]["id"]
                  and e.get("target_tenant") == target_tid]
        assert starts, f"No impersonation.start audit event found: {[e.get('action') for e in events[:5]]}"

        # Create a client while impersonating -> should belong to tenant B
        cname = f"TEST_imp_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/clients", headers=_hdr(imp_tok),
                          json={"name": cname, "email": "x@y.com"})
        assert r.status_code in (200, 201), r.text
        new_client_id = r.json()["id"]

        # Verify in mongo the client tenant_id == target_tid
        db = _mongo()
        c = db.clients.find_one({"id": new_client_id})
        assert c and c.get("tenant_id") == target_tid, f"client tenant={c.get('tenant_id')} expected {target_tid}"

        # GET /clients under impersonation returns tenant_b's clients (containing new_client_id)
        r = requests.get(f"{BASE}/clients", headers=_hdr(imp_tok))
        assert r.status_code == 200
        assert any(cl["id"] == new_client_id for cl in r.json())

        # Stop impersonation
        r = requests.post(f"{BASE}/platform/impersonate/stop", headers=_hdr(imp_tok))
        assert r.status_code == 200, r.text
        restored_tok = r.json()["access_token"]

        # Under restored token, /me should be maher's original tenant
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(restored_tok))
        assert r.status_code == 200
        d = r.json()
        assert d["tenant"]["id"] == maher["user"]["tenant_id"]
        assert not d["user"].get("impersonating_from")

        # And /clients on restored token must NOT include the tenant_b client
        r = requests.get(f"{BASE}/clients", headers=_hdr(restored_tok))
        assert r.status_code == 200
        assert not any(cl["id"] == new_client_id for cl in r.json()), "Impersonation leaked target tenant data!"

    def test_regular_user_cannot_impersonate(self, regular, tenant_b):
        r = requests.post(f"{BASE}/platform/impersonate",
                          headers=_hdr(regular["token"]),
                          json={"tenant_id": tenant_b["tenant"]["id"]})
        assert r.status_code == 403, r.text


# ------------------------ REGRESSION -----------------------

class TestRegression:
    def test_health(self):
        r = requests.get(f"{BASE}/health")
        assert r.status_code == 200

    def test_login_regular(self, regular):
        assert regular["token"]

    def test_me_regular(self, regular):
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(regular["token"]))
        assert r.status_code == 200

    def test_clients_crud(self, regular):
        r = requests.post(f"{BASE}/clients", headers=_hdr(regular["token"]),
                          json={"name": f"TEST_reg_{uuid.uuid4().hex[:6]}"})
        assert r.status_code in (200, 201)
        cid = r.json()["id"]
        r = requests.get(f"{BASE}/clients/{cid}", headers=_hdr(regular["token"]))
        assert r.status_code == 200
        r = requests.delete(f"{BASE}/clients/{cid}", headers=_hdr(regular["token"]))
        assert r.status_code in (200, 204)

    def test_module_toggle(self, regular):
        h = _hdr(regular["token"])
        r = requests.post(f"{BASE}/tenants/me/modules", headers=h,
                          json={"module": "crm", "enabled": False})
        assert r.status_code == 200
        r = requests.get(f"{BASE}/clients", headers=h)
        assert r.status_code == 403
        r = requests.post(f"{BASE}/tenants/me/modules", headers=h,
                          json={"module": "crm", "enabled": True})
        assert r.status_code == 200

    def test_billing_plans(self):
        r = requests.get(f"{BASE}/billing/plans")
        assert r.status_code == 200
        assert r.json().get("configured") is True

    def test_calendar_dormant(self, regular):
        r = requests.get(f"{BASE}/calendar/status", headers=_hdr(regular["token"]))
        assert r.status_code == 200
        assert r.json().get("connected") is False

    def test_dashboard(self, regular):
        r = requests.get(f"{BASE}/dashboard/overview", headers=_hdr(regular["token"]))
        assert r.status_code == 200

    def test_invoice_pdf(self, regular):
        h = _hdr(regular["token"])
        r = requests.post(f"{BASE}/invoices", headers=h, json={
            "client_name": "TEST_pdf",
            "items": [{"description": "x", "quantity": 1, "unit_price": 10, "tax_rate": 0}],
        })
        assert r.status_code in (200, 201)
        iid = r.json()["id"]
        r = requests.get(f"{BASE}/invoices/{iid}/pdf", headers=h)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
