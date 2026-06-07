"""Object storage for invoice files (FR-002, SRS §3.4 encryption + data localization).

Files are encrypted (AES-256-class) *before* leaving the app, then stored in S3 (ap-south-1)
or MinIO. When no S3 endpoint is configured we fall back to an encrypted local directory so
the MVP runs anywhere. Either way the stored bytes are ciphertext.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.security import _fernet


def _use_s3() -> bool:
    return bool(settings.S3_ENDPOINT_URL and settings.S3_ACCESS_KEY)


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def put_invoice_file(tenant_id: str, file_bytes: bytes, file_name: str) -> str:
    """Encrypt and store; return the storage key."""
    ciphertext = _fernet().encrypt(file_bytes)
    key = f"{tenant_id}/{uuid.uuid4().hex}_{file_name}"

    if _use_s3():
        client = _s3_client()
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            client.create_bucket(Bucket=settings.S3_BUCKET)
        client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=ciphertext)
    else:
        path = Path(settings.LOCAL_STORAGE_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ciphertext)
    return key


def get_invoice_file(key: str) -> bytes:
    """Fetch and decrypt the original file bytes."""
    if _use_s3():
        obj = _s3_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
        ciphertext = obj["Body"].read()
    else:
        ciphertext = (Path(settings.LOCAL_STORAGE_DIR) / key).read_bytes()
    return _fernet().decrypt(ciphertext)


def delete_invoice_file(key: str) -> None:
    if _use_s3():
        _s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    else:
        p = Path(settings.LOCAL_STORAGE_DIR) / key
        if p.exists():
            os.remove(p)
