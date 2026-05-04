from fastapi import APIRouter

from ..auth import CurrentUser, DbSession
from ..models import AuditLog, UserSettings
from ..schemas import AuditLogItem, UserSettingsModel, UserSettingsUpdate


router = APIRouter(tags=["audit & settings"])


@router.get("/audit-logs", response_model=list[AuditLogItem])
def list_audit_logs(user: CurrentUser, db: DbSession, limit: int = 200):
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .order_by(AuditLog.id.desc())
        .limit(min(limit, 1000))
        .all()
    )
    return rows


@router.get("/settings", response_model=UserSettingsModel)
def get_settings(user: CurrentUser, db: DbSession):
    s = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not s:
        s = UserSettings(user_id=user.id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.put("/settings", response_model=UserSettingsModel)
def update_settings(payload: UserSettingsUpdate, user: CurrentUser, db: DbSession):
    s = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not s:
        s = UserSettings(user_id=user.id)
        db.add(s)
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, val)
    db.commit()
    db.refresh(s)
    return s
