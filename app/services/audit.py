from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger("engagement.audit")


def record_audit_log(
    db: Session,
    *,
    action: str,
    actor_email: str,
    actor_role: str = "system",
    actor_id: str | None = None,
    organization_id: str | None = None,
    resource_type: str = "system",
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog | None:
    """
    Safely records an audit log entry.
    Flushes the record to the session so it is saved with the active transaction.
    """
    try:
        log = AuditLog(
            action=action,
            actor_email=actor_email,
            actor_role=actor_role,
            actor_id=actor_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(log)
        db.flush()
        logger.info("AUDIT [%s] by %s (%s): %s", action, actor_email, actor_role, details or "")
        return log
    except Exception as exc:
        logger.warning("Failed to record audit log: %s", exc)
        return None
