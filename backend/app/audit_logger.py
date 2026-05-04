"""Append-only audit logging for every user command, parsed output, and order attempt."""
from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog


def _scrub(payload: Any) -> Any:
    """Recursively redact any field that smells like an API secret."""
    if isinstance(payload, dict):
        cleaned = {}
        for k, v in payload.items():
            kl = str(k).lower()
            if kl in {"api_secret", "api_key", "secret", "password", "private_key"}:
                cleaned[k] = "***REDACTED***"
            else:
                cleaned[k] = _scrub(v)
        return cleaned
    if isinstance(payload, list):
        return [_scrub(v) for v in payload]
    return payload


def log_event(
    db: Session,
    *,
    user_id: int | None,
    event_type: str,
    raw_command: str | None = None,
    parsed_payload: dict | None = None,
    result_payload: dict | None = None,
    success: bool = True,
    message: str | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        raw_command=raw_command,
        parsed_payload=_scrub(parsed_payload) if parsed_payload is not None else None,
        result_payload=_scrub(result_payload) if result_payload is not None else None,
        success=success,
        message=message,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
