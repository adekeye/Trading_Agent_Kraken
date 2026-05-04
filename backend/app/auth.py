"""Authentication: password hashing and JWT issuance/verification."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(user_id: int) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.jwt_expires_minutes)
    expire = datetime.now(tz=timezone.utc) + expires_delta
    payload = {"sub": str(user_id), "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def get_current_user(
    token: Annotated[str, Depends(_oauth2)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise creds_exc

    user = db.get(User, user_id)
    if user is None:
        raise creds_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
