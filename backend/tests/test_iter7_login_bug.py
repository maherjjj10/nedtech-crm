"""Iteration 7 — Platform Owner login bug regression tests."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
# Frontend .env holds REACT_APP_BACKEND_URL — fall back
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api/v1"
EMAIL = "maher@tapbyned.com"
PASSWORD = "NedTechOwner2026!"


def test_login_baseline_ok():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"].lower() == EMAIL


def test_login_whitespace_email_ok():
    r = requests.post(f"{API}/auth/login", json={"email": f"  {EMAIL}  ", "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"].lower() == EMAIL


def test_login_case_insensitive_email_ok():
    r = requests.post(f"{API}/auth/login", json={"email": "Maher@TAPBYNED.com", "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text


def test_login_wrong_password_401():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": "WRONGPASSWORD"}, timeout=15)
    assert r.status_code == 401
    assert "Invalid email or password" in r.text


def test_login_empty_password_fails():
    # EmailStr valid + empty password → 401 or 422 (validation)
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": ""}, timeout=15)
    assert r.status_code in (401, 422), r.text


def test_password_still_the_seed_value():
    """Guardrails: ensure platform owner password wasn't rotated during testing."""
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, "Platform owner password appears to have been changed — must be reset to NedTechOwner2026!"
