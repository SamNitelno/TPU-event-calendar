"""Database sessions, scrypt password hashes and CSRF protection for administrators."""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from db.database import get_db
from db.models import AdminSession

COOKIE_NAME = "tpu_admin"
SESSION_SECONDS = 12 * 60 * 60


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, expected = stored.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return hmac.new(token.encode(), b"tpu-calendar-csrf", hashlib.sha256).hexdigest()


def secure_cookie() -> bool:
    return os.getenv("VERCEL") == "1" or os.getenv("COOKIE_SECURE") == "1"


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Недопустимый источник запроса")


def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminSession:
    token = request.cookies.get(COOKIE_NAME, "")
    session = (
        db.scalar(
            select(AdminSession)
            .options(joinedload(AdminSession.user))
            .where(
                AdminSession.token_hash == token_hash(token),
                AdminSession.expires_at > utcnow(),
            )
        )
        if token
        else None
    )
    if session is None:
        raise HTTPException(401, "Войдите как администратор")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), csrf_token(token)):
            raise HTTPException(403, "Обновите страницу и повторите действие")
    return session


def new_session(user_id: int):
    token = secrets.token_urlsafe(32)
    return token, AdminSession(
        token_hash=token_hash(token), user_id=user_id, expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS)
    )
