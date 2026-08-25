from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import get_session
from .models import AuthSession, User

SESSION_COOKIE = "rubricheck_session"
SESSION_DAYS = 14


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), f"{salt}${digest}")


def issue_session(response: Response, user: User, session: Session) -> None:
    raw_token = secrets.token_urlsafe(32)
    expiry = datetime.now(UTC) + timedelta(days=SESSION_DAYS)
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at < datetime.now(UTC)))
    session.add(AuthSession(user_id=user.id, token_hash=sha256(raw_token.encode()).hexdigest(), expires_at=expiry))
    session.commit()
    response.set_cookie(SESSION_COOKIE, raw_token, httponly=True, samesite="lax", secure=False, max_age=SESSION_DAYS * 86400)


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    session: Session = Depends(get_session),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    record = session.scalar(select(AuthSession).where(AuthSession.token_hash == sha256(session_token.encode()).hexdigest(), AuthSession.expires_at > datetime.now(UTC)))
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")
    user = session.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    return user
