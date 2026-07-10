from typing import Any
from sqlalchemy.orm import Session
from ..models import AuditLog, User


def record_audit(
    db: Session,
    event_type: str,
    actor: User | None = None,
    organization_id: int | None = None,
    repository_id: int | None = None,
    pull_request_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    result: str = "success",
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id if actor else None,
        organization_id=organization_id or (actor.organization_id if actor else None),
        repository_id=repository_id,
        pull_request_id=pull_request_id,
        event_type=event_type,
        old_value=old_value,
        new_value=new_value,
        result=result,
        ip_address=ip_address,
    )
    db.add(log)
    return log
