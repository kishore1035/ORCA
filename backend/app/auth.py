"""Password hashing and JWT session tokens.

Minimal, real auth (per an explicit scope decision): email + password only,
no OAuth, no email verification, no password reset. Hashing uses stdlib
hashlib.pbkdf2_hmac (no new crypto dependency); tokens use PyJWT.
"""
import hashlib
import os
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

PBKDF2_ITERATIONS = 260_000
TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days -- a demo app, not a bank


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex() == password_hash


def create_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
