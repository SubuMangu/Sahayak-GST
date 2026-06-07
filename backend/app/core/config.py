"""Application configuration (SRS §4 / §3.4 data localization).

All settings are environment-driven via pydantic-settings. Sensible dev defaults are
provided so the stack runs locally with zero paid keys (mock providers).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    APP_NAME: str = "Sahayak GST"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    ENCRYPTION_KEY: str = ""  # Fernet key; auto-derived from SECRET_KEY if blank (dev only)

    # Data localization (SRS §3.4): default to Mumbai region
    DATA_REGION: str = "ap-south-1"

    # Database — sqlite fallback keeps `pytest` and `uvicorn --reload` zero-config.
    DATABASE_URL: str = "sqlite+aiosqlite:///./sahayak.db"

    # Cache / queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object storage
    S3_ENDPOINT_URL: str = ""
    S3_REGION: str = "ap-south-1"
    S3_BUCKET: str = "sahayak-invoices"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    LOCAL_STORAGE_DIR: str = "./storage"  # used when S3 not configured

    # AI extraction
    EXTRACTION_PROVIDER: str = "mock"  # mock | openai-compatible | anthropic
    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # WhatsApp
    WHATSAPP_PROVIDER: str = "mock"
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "sahayak-verify"

    # SMS / OTP
    SMS_PROVIDER: str = "mock"
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    OTP_TTL_SECONDS: int = 300
    OTP_LENGTH: int = 6

    # Email
    EMAIL_PROVIDER: str = "mock"
    EMAIL_FROM: str = "noreply@sahayakgst.in"
    RESEND_API_KEY: str = ""

    # Payments
    RAZORPAY_PROVIDER: str = "mock"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # GSTN public search
    GSTN_SEARCH_ENABLED: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
