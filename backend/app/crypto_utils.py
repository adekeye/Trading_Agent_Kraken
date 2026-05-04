"""Encryption helpers for storing Kraken API credentials at rest."""
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


def _resolve_fernet_key() -> bytes:
    """Build a valid Fernet key from settings.encryption_key.

    If the key is already a valid 32-byte urlsafe-base64 value, use it as-is.
    Otherwise, derive a deterministic 32-byte key by SHA-256 hashing the secret.
    The latter is a development convenience; production should set a real Fernet key.
    """
    settings = get_settings()
    raw = settings.encryption_key or settings.jwt_secret

    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == 32:
            return raw.encode() if isinstance(raw, str) else raw
    except Exception:
        pass

    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_FERNET = Fernet(_resolve_fernet_key())


def encrypt_secret(plain: str) -> str:
    return _FERNET.encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _FERNET.decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted secret token") from exc
