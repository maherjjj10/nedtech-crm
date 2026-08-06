"""Password hashing and JWT tokens."""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(payload: dict[str, Any], expires_in_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = expires_in_minutes if expires_in_minutes is not None else settings.JWT_EXPIRE_MINUTES
    body = {
        **payload,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "iss": "nedtech-crm",
    }
    return jwt.encode(body, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        issuer="nedtech-crm",
    )
