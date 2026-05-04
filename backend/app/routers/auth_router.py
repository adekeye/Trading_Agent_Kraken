from fastapi import APIRouter, HTTPException, status

from .. import audit_logger
from ..auth import (
    CurrentUser,
    DbSession,
    create_access_token,
    hash_password,
    verify_password,
)
from ..models import User, UserSettings
from ..schemas import LoginRequest, RegisterRequest, TokenResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: DbSession):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    db.commit()
    db.refresh(user)
    audit_logger.log_event(db, user_id=user.id, event_type="user_registered")
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    audit_logger.log_event(db, user_id=user.id, event_type="user_login")
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "email": user.email}
