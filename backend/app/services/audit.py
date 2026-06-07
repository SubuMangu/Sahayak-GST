"""Audit logging helper (SRS §3.4): record access/changes to financial records."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log(
    db: AsyncSession,
    *,
    action: str,
    tenant_id: str | None = None,
    user_id: str | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            ip_address=ip_address,
            detail=detail,
        )
    )
    await db.flush()
