"""Iteration 9 tests: forgot/reset password + session management."""
import os
import re
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    # fallback to frontend env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.strip().split("=", 1)[1].rstrip("/")
API = f"{BASE}/api/v1"

OWNER_EMAIL = "maher@tapbyned.com"
OWNER_PASS = "NedTechOwner2026!"
TEMP_PASS = "ResetTest2026!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


def _forgot(email):
    return requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30)


def _reset(token, new_password):
    return requests.post(f"{API}/auth/reset-password", json={"token": token, "new_password": new_password}, timeout=30)


def _extract_token(dev_url: str) -> str:
    # /auth/reset-password/<token>
    m = re.search(r"/auth/reset-password/([^/?#]+)$", dev_url)
    assert m, f"could not parse token from {dev_url}"
    return m.group(1)


def _me(access_token: str):
    return requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=30)


@pytest.fixture(scope="module")
def restore_password():
    """Ensure password is restored to OWNER_PASS at end of module."""
    yield
    # attempt login with owner pass; if works, skip
    r = _login(OWNER_EMAIL, OWNER_PASS)
    if r.status_code == 200:
        return
    # otherwise reset back via forgot flow
    fr = _forgot(OWNER_EMAIL)
    if fr.status_code == 200 and "dev_reset_url" in fr.json():
        token = _extract_token(fr.json()["dev_reset_url"])
        _reset(token, OWNER_PASS)


def test_01_forgot_password_happy_path(restore_password):
    r = _forgot(OWNER_EMAIL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "dev_reset_url" in body, f"Expected dev_reset_url when email not configured, got {body}"
    token = _extract_token(body["dev_reset_url"])

    # Reset
    rr = _reset(token, TEMP_PASS)
    assert rr.status_code == 200, rr.text
    assert rr.json().get("ok") is True

    # Old password should now fail
    old = _login(OWNER_EMAIL, OWNER_PASS)
    assert old.status_code == 401, f"Old password should be rejected, got {old.status_code}: {old.text}"

    # New password should work
    new = _login(OWNER_EMAIL, TEMP_PASS)
    assert new.status_code == 200, new.text

    # Restore back
    fr2 = _forgot(OWNER_EMAIL)
    assert fr2.status_code == 200
    token2 = _extract_token(fr2.json()["dev_reset_url"])
    rr2 = _reset(token2, OWNER_PASS)
    assert rr2.status_code == 200
    back = _login(OWNER_EMAIL, OWNER_PASS)
    assert back.status_code == 200, "Failed to restore original password"


def test_02_forgot_password_anti_enumeration():
    r = _forgot("nonexistent-xyz@nowhere-example.com")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "dev_reset_url" not in body, "dev_reset_url leaked for nonexistent email"


def test_03_reset_token_reuse_and_invalid():
    # invalid token
    r = _reset("this-is-not-a-real-token", "SomePass1234!")
    assert r.status_code == 400

    # request token, use it once, try again
    fr = _forgot(OWNER_EMAIL)
    token = _extract_token(fr.json()["dev_reset_url"])
    r1 = _reset(token, OWNER_PASS)  # reset to same pass (still valid)
    assert r1.status_code == 200
    r2 = _reset(token, OWNER_PASS)
    assert r2.status_code == 400
    assert "already been used" in r2.text.lower() or "already" in r2.text.lower()

    # confirm login still works
    ok = _login(OWNER_EMAIL, OWNER_PASS)
    assert ok.status_code == 200


def test_04_reset_revokes_all_sessions():
    a = _login(OWNER_EMAIL, OWNER_PASS)
    b = _login(OWNER_EMAIL, OWNER_PASS)
    assert a.status_code == 200 and b.status_code == 200
    tok_a = a.json()["access_token"]
    tok_b = b.json()["access_token"]
    assert _me(tok_a).status_code == 200
    assert _me(tok_b).status_code == 200

    # forgot + reset
    fr = _forgot(OWNER_EMAIL)
    token = _extract_token(fr.json()["dev_reset_url"])
    rr = _reset(token, OWNER_PASS)
    assert rr.status_code == 200

    ra = _me(tok_a)
    rb = _me(tok_b)
    assert ra.status_code == 401, f"token A should be revoked, got {ra.status_code}"
    assert rb.status_code == 401, f"token B should be revoked, got {rb.status_code}"


def test_05_login_issues_jti_and_lists_session():
    import base64, json
    r = _login(OWNER_EMAIL, OWNER_PASS)
    assert r.status_code == 200
    tok = r.json()["access_token"]
    # decode JWT payload
    payload_b64 = tok.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    assert "jti" in claims, f"jti missing from token: {claims}"

    # list sessions
    ls = requests.get(f"{API}/profile/sessions", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    assert ls.status_code == 200, ls.text
    sessions = ls.json()
    assert len(sessions) >= 1
    current = [s for s in sessions if s.get("is_current")]
    assert len(current) == 1, f"expected exactly 1 current session, got {len(current)}"
    s = current[0]
    assert "device" in s and s["device"]
    assert "ip" in s  # ip may be None but key must exist


def test_06_revoke_single_session():
    a = _login(OWNER_EMAIL, OWNER_PASS)
    b = _login(OWNER_EMAIL, OWNER_PASS)
    tok_a = a.json()["access_token"]
    tok_b = b.json()["access_token"]

    # from tok_a, list sessions and find B's sid (the non-current)
    ls = requests.get(f"{API}/profile/sessions", headers={"Authorization": f"Bearer {tok_a}"}, timeout=30).json()
    non_current = [s for s in ls if not s.get("is_current")]
    assert non_current, "expected at least one other session"
    # pick most recent one (which should be B, since it just logged in)
    sid_b = non_current[0]["id"]

    dr = requests.delete(f"{API}/profile/sessions/{sid_b}", headers={"Authorization": f"Bearer {tok_a}"}, timeout=30)
    assert dr.status_code == 204, dr.text

    rb = _me(tok_b)
    assert rb.status_code == 401
    assert "signed out" in rb.text.lower() or "session" in rb.text.lower()

    ra = _me(tok_a)
    assert ra.status_code == 200


def test_07_revoke_others():
    a = _login(OWNER_EMAIL, OWNER_PASS)
    b = _login(OWNER_EMAIL, OWNER_PASS)
    c = _login(OWNER_EMAIL, OWNER_PASS)
    tok_a = a.json()["access_token"]
    tok_b = b.json()["access_token"]
    tok_c = c.json()["access_token"]

    ro = requests.post(f"{API}/profile/sessions/revoke-others",
                       headers={"Authorization": f"Bearer {tok_a}"}, timeout=30)
    assert ro.status_code == 200, ro.text
    revoked = ro.json().get("revoked", 0)
    assert revoked >= 2, f"expected >=2 sessions revoked, got {revoked}"

    assert _me(tok_a).status_code == 200
    assert _me(tok_b).status_code == 401
    assert _me(tok_c).status_code == 401


def test_08_regression_login_and_me():
    r = _login(OWNER_EMAIL, OWNER_PASS)
    assert r.status_code == 200
    tok = r.json()["access_token"]
    m = _me(tok)
    assert m.status_code == 200
    assert m.json()["user"]["email"] == OWNER_EMAIL


def test_09_regression_crm_crud():
    r = _login(OWNER_EMAIL, OWNER_PASS)
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # clients list
    cl = requests.get(f"{API}/clients", headers=h, timeout=30)
    assert cl.status_code == 200

    # create client
    new_c = requests.post(f"{API}/clients", headers=h,
                          json={"name": "TEST_iter9_client", "email": "iter9@example.com"}, timeout=30)
    assert new_c.status_code in (200, 201), new_c.text
    cid = new_c.json().get("id")
    assert cid

    # get client
    gc = requests.get(f"{API}/clients/{cid}", headers=h, timeout=30)
    assert gc.status_code == 200

    # delete
    dc = requests.delete(f"{API}/clients/{cid}", headers=h, timeout=30)
    assert dc.status_code in (200, 204)


def test_zz_final_restore_password():
    """Ensure password is at OWNER_PASS at the very end."""
    r = _login(OWNER_EMAIL, OWNER_PASS)
    assert r.status_code == 200, "Password not restored to original!"
