"""Crypto and JWT utilities. No DB access.

Two responsibilities:
  - password hashing/verification (bcrypt directly — passlib is abandoned
    and breaks on bcrypt >= 4.1 due to a removed version-detection hook)
  - JWT encode/decode (HS256 via python-jose)
"""
from datetime import datetime, timedelta, timezone
from typing import List

import bcrypt
from jose import jwt

from src.config.env_loader import env
from src.models.auth_models import TokenPayload




def _to_bcrypt_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    return raw[:72] if len(raw) > 72 else raw


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except Exception:
        return False


def _build_payload(
    *,
    user_id: str,
    email: str,
    name: str,
    is_global_admin: bool,
    token_type: str,
    expires_delta: timedelta,
) -> dict:
    now = datetime.now(timezone.utc)
    exp = now + expires_delta
    return {
        "sub": user_id,
        "email": email,
        "name": name,
        "isGlobalAdmin": is_global_admin,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }


def create_access_token(
    *,
    user_id: str,
    email: str,
    name: str,
    is_global_admin: bool,
) -> str:
    payload = _build_payload(
        user_id=user_id,
        email=email,
        name=name,
        is_global_admin=is_global_admin,
        token_type="access",
        expires_delta=timedelta(minutes=env.JWT_ACCESS_EXPIRE_MINUTES),
    )
    return jwt.encode(payload, env.JWT_SECRET, algorithm=env.JWT_ALGORITHM)


def create_refresh_token(
    *,
    user_id: str,
    email: str,
    name: str,
    is_global_admin: bool,
) -> str:
    payload = _build_payload(
        user_id=user_id,
        email=email,
        name=name,
        is_global_admin=is_global_admin,
        token_type="refresh",
        expires_delta=timedelta(days=env.JWT_REFRESH_EXPIRE_DAYS),
    )
    return jwt.encode(payload, env.JWT_SECRET, algorithm=env.JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate signature/expiry. Raises JWTError on failure."""
    raw = jwt.decode(token, env.JWT_SECRET, algorithms=[env.JWT_ALGORITHM])
    return TokenPayload(**raw)