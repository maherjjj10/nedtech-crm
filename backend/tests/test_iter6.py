"""Iteration 6 backend tests:
- Profile update (/profile/me)
- Change password happy + errors + persistence across restart
- Global platform search (/platform/search)
- 30-minute impersonation TTL
- Grant super_admin permission ceiling
- Iter-5 regression sanity (protected owner, impersonation re-scoping, audit)
"""
import os
import time
import uuid
import subprocess

import jwt as pyjwt
import pytest
import requests
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
    return requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw})


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def _wait_backend(timeout=30):
    for _ in range(timeout):
        try:
            if requests.get(f"{BASE}/health", timeout=3).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ------------------------ FIXTURES ------------------------

@pytest.fixture(scope="module")
def maher():
    r = _login(OWNER_EMAIL, OWNER_PASS)
    assert r.status_code == 200, f"platform owner login failed: {r.status_code} {r.text}"
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "tenant": d["tenant"]}


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def tenant_b():
    email = f"tb6_{uuid.uuid4().hex[:8]}@nedtech.example.com"
    r = requests.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Password123!",
        "name": "Owner B6", "company_name": f"Tenant B6 {uuid.uuid4().hex[:6]}"})
    assert r.status_code in (200, 201), r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "tenant": d["tenant"], "email": email}


# ------------------------ PROFILE UPDATE ------------------------

class TestProfileUpdate:
    def test_patch_profile_me(self, maher):
        new_name = f"Maher Updated {uuid.uuid4().hex[:4]}"
        r = requests.patch(f"{BASE}/profile/me",
                           headers=_hdr(maher["token"]),
                           json={"name": new_name, "phone": "+123"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == new_name
        assert body.get("phone") == "+123"
        assert "password_hash" not in body

        # /auth/me reflects new name
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        assert r.json()["user"]["name"] == new_name


# ------------------------ CHANGE PASSWORD ------------------------

class TestChangePassword:
    NEW_PASS = "BrandNew2026!"

    def test_change_password_happy_and_persist(self, maher):
        # 1. change from OWNER_PASS -> NEW_PASS
        r = requests.post(f"{BASE}/profile/change-password",
                          headers=_hdr(maher["token"]),
                          json={"current_password": OWNER_PASS,
                                "new_password": self.NEW_PASS})
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # 2. old password fails
        r = _login(OWNER_EMAIL, OWNER_PASS)
        assert r.status_code == 401, r.text

        # 3. new password works
        r = _login(OWNER_EMAIL, self.NEW_PASS)
        assert r.status_code == 200, r.text
        new_tok = r.json()["access_token"]

        # 4. restart backend and login with new password
        subprocess.run(["sudo", "supervisorctl", "restart", "backend"],
                       check=True, capture_output=True)
        assert _wait_backend(30), "backend did not come back after restart"

        r = _login(OWNER_EMAIL, self.NEW_PASS)
        assert r.status_code == 200, f"seed clobbered password! {r.status_code} {r.text}"

        # 5. reset back to original so future tests unaffected
        tok = r.json()["access_token"]
        r = requests.post(f"{BASE}/profile/change-password",
                          headers=_hdr(tok),
                          json={"current_password": self.NEW_PASS,
                                "new_password": OWNER_PASS})
        assert r.status_code == 200, r.text
        # confirm login with original works
        r = _login(OWNER_EMAIL, OWNER_PASS)
        assert r.status_code == 200

    def test_change_password_wrong_current(self, maher):
        # re-login (fixture token may be from before restart, but still valid JWT)
        r = _login(OWNER_EMAIL, OWNER_PASS)
        assert r.status_code == 200
        tok = r.json()["access_token"]
        r = requests.post(f"{BASE}/profile/change-password",
                          headers=_hdr(tok),
                          json={"current_password": "WrongPass!!", "new_password": "NewPass1234!"})
        assert r.status_code == 401, r.text

    def test_change_password_too_short(self):
        r = _login(OWNER_EMAIL, OWNER_PASS)
        tok = r.json()["access_token"]
        r = requests.post(f"{BASE}/profile/change-password",
                          headers=_hdr(tok),
                          json={"current_password": OWNER_PASS, "new_password": "short"})
        assert r.status_code == 422, r.text

    def test_change_password_same_as_current(self):
        r = _login(OWNER_EMAIL, OWNER_PASS)
        tok = r.json()["access_token"]
        r = requests.post(f"{BASE}/profile/change-password",
                          headers=_hdr(tok),
                          json={"current_password": OWNER_PASS, "new_password": OWNER_PASS})
        assert r.status_code == 400, r.text


# ------------------------ GLOBAL SEARCH ------------------------

class TestGlobalSearch:
    def test_search_ok(self, maher):
        r = requests.get(f"{BASE}/platform/search",
                         params={"q": "ned"},
                         headers=_hdr(maher["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("tenants", "users", "invoices", "clients"):
            assert k in data
            assert isinstance(data[k], list)

    def test_search_short_query(self, maher):
        r = requests.get(f"{BASE}/platform/search",
                         params={"q": "a"},
                         headers=_hdr(maher["token"]))
        assert r.status_code == 200
        data = r.json()
        assert data == {"tenants": [], "users": [], "invoices": [], "clients": []}

    def test_search_forbidden_for_non_platform(self, regular):
        r = requests.get(f"{BASE}/platform/search",
                         params={"q": "ned"},
                         headers=_hdr(regular["token"]))
        assert r.status_code == 403, r.text


# ------------------------ IMPERSONATION TTL ------------------------

class TestImpersonationTTL:
    def test_impersonation_ttl_30_minutes(self, maher, tenant_b):
        r = requests.post(f"{BASE}/platform/impersonate",
                          headers=_hdr(maher["token"]),
                          json={"tenant_id": tenant_b["tenant"]["id"], "reason": "ttl test"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("expires_in_minutes") == 30, body
        tok = body["access_token"]
        decoded = pyjwt.decode(tok, options={"verify_signature": False})
        assert "exp" in decoded and "iat" in decoded
        diff = decoded["exp"] - decoded["iat"]
        assert 1740 <= diff <= 1860, f"exp-iat={diff}, expected ~1800"

        # cleanup — stop impersonation so subsequent tests aren't blocked
        requests.post(f"{BASE}/platform/impersonate/stop", headers=_hdr(tok))


# ------------------------ GRANT SUPER_ADMIN ------------------------

class TestGrantSuperAdmin:
    def test_owner_grants_super_admin_and_revokes(self, maher, tenant_b):
        uid = tenant_b["user"]["id"]

        # grant
        r = requests.patch(f"{BASE}/platform/users/{uid}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": "super_admin"})
        assert r.status_code == 200, r.text
        assert r.json().get("platform_role") == "super_admin"

        # re-login to receive fresh JWT with platform_role claim
        r = _login(tenant_b["email"], "Password123!")
        assert r.status_code == 200
        sa_tok = r.json()["access_token"]
        assert r.json()["user"].get("platform_role") == "super_admin"

        # can access /platform/tenants
        r = requests.get(f"{BASE}/platform/tenants", headers=_hdr(sa_tok))
        assert r.status_code == 200, r.text

        # revoke via PATCH with platform_role=""
        r = requests.patch(f"{BASE}/platform/users/{uid}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": ""})
        assert r.status_code == 200, r.text
        # after clearing, DB should be None
        db = _mongo()
        u = db.users.find_one({"id": uid})
        assert u.get("platform_role") in (None, "")

    def test_super_admin_cannot_grant_super_admin(self, maher, tenant_b):
        db = _mongo()
        uid = tenant_b["user"]["id"]
        # promote tenant_b to super_admin
        r = requests.patch(f"{BASE}/platform/users/{uid}/role",
                           headers=_hdr(maher["token"]),
                           json={"platform_role": "super_admin"})
        assert r.status_code == 200
        r = _login(tenant_b["email"], "Password123!")
        sa_tok = r.json()["access_token"]

        # find another non-owner user
        other = db.users.find_one({
            "platform_role": {"$in": [None, ""]},
            "email": {"$ne": OWNER_EMAIL},
            "id": {"$ne": uid},
        })
        assert other, "need another user for this test"

        # super_admin tries to grant super_admin -> 403
        r = requests.patch(f"{BASE}/platform/users/{other['id']}/role",
                           headers=_hdr(sa_tok),
                           json={"platform_role": "super_admin"})
        assert r.status_code == 403, r.text
        assert "platform_owner" in r.text.lower() or "only" in r.text.lower()

        # cannot grant platform_owner
        r = requests.patch(f"{BASE}/platform/users/{other['id']}/role",
                           headers=_hdr(sa_tok),
                           json={"platform_role": "platform_owner"})
        assert r.status_code == 403, r.text

        # cleanup: demote tenant_b back to None
        db.users.update_one({"id": uid}, {"$set": {"platform_role": None}})


# ------------------------ REGRESSION ------------------------

class TestRegression:
    def test_protected_owner_undeletable(self, maher):
        uid = maher["user"]["id"]
        r = requests.delete(f"{BASE}/platform/users/{uid}", headers=_hdr(maher["token"]))
        assert r.status_code == 403, r.text

    def test_impersonation_rescopes_and_audits(self, maher, tenant_b):
        target = tenant_b["tenant"]["id"]
        r = requests.post(f"{BASE}/platform/impersonate",
                          headers=_hdr(maher["token"]),
                          json={"tenant_id": target, "reason": "regression"})
        assert r.status_code == 200
        imp_tok = r.json()["access_token"]

        # /clients under impersonation should be tenant_b scope
        r = requests.get(f"{BASE}/clients", headers=_hdr(imp_tok))
        assert r.status_code == 200

        # /auth/me tenant is target
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(imp_tok))
        assert r.status_code == 200
        assert r.json()["tenant"]["id"] == target

        # audit contains role.change or user.role_change entries (from earlier tests)
        r = requests.get(f"{BASE}/platform/audit", headers=_hdr(maher["token"]))
        assert r.status_code == 200
        events = r.json()
        assert any(e.get("action") in ("user.role_change", "role.change") for e in events), \
            "no role change audit event found"

        # stop
        requests.post(f"{BASE}/platform/impersonate/stop", headers=_hdr(imp_tok))
