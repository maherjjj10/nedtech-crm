"""Application configuration.

All settings are loaded from environment variables. No hardcoded secrets.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# Load backend/.env
load_dotenv(
    Path(__file__).resolve().parents[2] / ".env"
)


class Settings:
    # ============================================================
    # DATABASE
    # ============================================================

    MONGO_URL: str = os.environ["MONGO_URL"]
    DB_NAME: str = os.environ["DB_NAME"]

    # ============================================================
    # SECURITY
    # ============================================================

    JWT_SECRET: str = os.environ.get(
        "JWT_SECRET",
        "dev-secret-change-me",
    )

    JWT_ALGORITHM: str = os.environ.get(
        "JWT_ALGORITHM",
        "HS256",
    )

    JWT_EXPIRE_MINUTES: int = int(
        os.environ.get(
            "JWT_EXPIRE_MINUTES",
            "1440",
        )
    )

    # ============================================================
    # CORS / APPLICATION URLS
    # ============================================================

    CORS_ORIGINS: list = os.environ.get(
        "CORS_ORIGINS",
        "*",
    ).split(",")

    FRONTEND_URL: str = os.environ.get(
        "FRONTEND_URL",
        "http://localhost:3000",
    ).strip().strip('"').strip("'")

    PUBLIC_APP_URL: str = os.environ.get(
        "PUBLIC_APP_URL",
        "",
    ).strip().strip('"').strip("'")

    # Public application URL used for customer-facing links.
    #
    # Priority:
    # 1. PUBLIC_APP_URL
    # 2. FRONTEND_URL
    #
    # This prevents customer links from falling back to
    # an old platform/preview URL.

    @property
    def PUBLIC_URL(self) -> str:
        return (
            self.PUBLIC_APP_URL
            or self.FRONTEND_URL
        ).rstrip("/")

    # ============================================================
    # EMERGENT LLM
    # ============================================================

    EMERGENT_LLM_KEY: str = os.environ.get(
        "EMERGENT_LLM_KEY",
        "",
    )

    LLM_MODEL: str = os.environ.get(
        "LLM_MODEL",
        "gpt-5.4",
    )

    # ============================================================
    # GOOGLE OAUTH
    # ============================================================

    GOOGLE_CLIENT_ID: str = os.environ.get(
        "GOOGLE_CLIENT_ID",
        "",
    )

    GOOGLE_CLIENT_SECRET: str = os.environ.get(
        "GOOGLE_CLIENT_SECRET",
        "",
    )

    GOOGLE_REDIRECT_URI: str = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "",
    )

    # ============================================================
    # STRIPE
    # ============================================================

    STRIPE_SECRET_KEY: str = os.environ.get(
        "STRIPE_SECRET_KEY",
        "",
    )

    STRIPE_WEBHOOK_SECRET: str = os.environ.get(
        "STRIPE_WEBHOOK_SECRET",
        "",
    )

    # ============================================================
    # RESEND
    # ============================================================

    RESEND_API_KEY: str = os.environ.get(
        "RESEND_API_KEY",
        "",
    )

    EMAIL_FROM: str = os.environ.get(
        "EMAIL_FROM",
        "noreply@example.com",
    )

    # ============================================================
    # API
    # ============================================================

    API_V1_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()