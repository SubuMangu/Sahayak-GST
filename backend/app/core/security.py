"""Security primitives (SRS §3.4): JWT access/refresh, password hashing, field encryption.

- JWT access + short-lived refresh tokens.
- AES-256-class field encryption via Fernet (symmetric, authenticated) for sensitive DB
  fields and stored file pointers.
- Encryption key comes from ``ENCRYPTION_KEY`` or is derived from ``SECRET_KEY`` in dev.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Password hashing (used for optional CA/admin password accounts) ---
def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


# --- JWT ---
def _create_token(subject: str, expires_delta: timedelta, token_type: str, **claims: Any) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **claims,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: str, **claims: Any) -> str:
    return _create_token(
        user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access", **claims
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


# --- Field-level encryption (AES-256-class, authenticated) ---
def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        # Dev-only deterministic derivation from SECRET_KEY. In prod set ENCRYPTION_KEY.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_str(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    return _fernet().decrypt(ciphertext.encode()).decode()
