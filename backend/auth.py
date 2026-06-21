import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import Response

from config import settings
from time_utils import cn_now_naive

SessionRole = Literal["admin", "leader"]


def is_auth_enabled() -> bool:
    return bool(settings.ACCESS_PASSWORD.strip())


def is_leader_auth_enabled() -> bool:
    return bool(settings.LEADER_ACCESS_PASSWORD.strip())


def _cookie_secure() -> bool:
    return bool(settings.AUTH_COOKIE_SECURE)


def _session_secret() -> str:
    seed = f"{settings.ACCESS_PASSWORD}|{settings.LEADER_ACCESS_PASSWORD}|{settings.AUTH_COOKIE_NAME}|platform-session"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _sign_session(session_id: str, role: SessionRole) -> str:
    payload = f"{session_id}:{role}"
    signature = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def _sqlite_db_path() -> Path:
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if settings.DATABASE_URL.startswith(prefix):
            return Path(settings.DATABASE_URL[len(prefix):]).resolve()
    raise RuntimeError("Only sqlite DATABASE_URL is supported for auth sessions")


def _connect_db() -> sqlite3.Connection:
    path = _sqlite_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_auth_sessions_role ON auth_sessions (role)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires_at ON auth_sessions (expires_at)")
    return conn


def _cleanup_expired_sessions(conn: sqlite3.Connection) -> None:
    now_str = cn_now_naive().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (now_str,))
    conn.commit()


def _parse_session(cookie_value: str | None) -> tuple[str, SessionRole] | None:
    if not cookie_value:
        return None
    parts = cookie_value.split(":")
    if len(parts) != 3:
        return None
    session_id, role, signature = parts
    if role not in {"admin", "leader"}:
        return None
    expected = _sign_session(session_id, role)
    if not secrets.compare_digest(cookie_value, expected):
        return None
    return session_id, role


def _lookup_session(session_id: str) -> SessionRole | None:
    with closing(_connect_db()) as conn:
        row = conn.execute(
            """
            SELECT role
            FROM auth_sessions
            WHERE session_id = ?
              AND expires_at >= ?
            LIMIT 1
            """,
            (session_id, cn_now_naive().strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchone()
    if not row:
        return None
    role = row[0]
    return role if role in {"admin", "leader"} else None


def _store_session(session_id: str, role: SessionRole) -> None:
    now = cn_now_naive()
    expires_at = now + timedelta(hours=settings.AUTH_MAX_AGE_HOURS)
    with closing(_connect_db()) as conn:
        _cleanup_expired_sessions(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO auth_sessions (session_id, role, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                now.strftime("%Y-%m-%d %H:%M:%S"),
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()


def _delete_session(session_id: str) -> None:
    with closing(_connect_db()) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
        conn.commit()


def is_valid_auth_cookie(cookie_value: str | None) -> bool:
    if not is_auth_enabled():
        return True
    parsed = _parse_session(cookie_value)
    if not parsed:
        return False
    session_id, role = parsed
    return _lookup_session(session_id) == role


def is_admin_auth_cookie(cookie_value: str | None) -> bool:
    if not is_auth_enabled():
        return True
    parsed = _parse_session(cookie_value)
    if not parsed:
        return False
    session_id, role = parsed
    return role == "admin" and _lookup_session(session_id) == "admin"


def is_leader_auth_cookie(cookie_value: str | None) -> bool:
    if not is_leader_auth_enabled():
        return False
    parsed = _parse_session(cookie_value)
    if not parsed:
        return False
    session_id, role = parsed
    return role == "leader" and _lookup_session(session_id) == "leader"


def auth_role_from_cookie(cookie_value: str | None) -> str | None:
    parsed = _parse_session(cookie_value)
    if not parsed:
        return None if is_auth_enabled() else "admin"
    session_id, role = parsed
    if _lookup_session(session_id) == role:
        return role
    return None


def set_auth_cookie(response: Response, *, role: SessionRole = "admin") -> str:
    session_id = secrets.token_urlsafe(24)
    value = _sign_session(session_id, role)
    _store_session(session_id, role)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=value,
        max_age=settings.AUTH_MAX_AGE_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )
    return value


def clear_auth_cookie(response: Response, *, cookie_value: str | None = None) -> None:
    parsed = _parse_session(cookie_value)
    if parsed:
        session_id, _ = parsed
        _delete_session(session_id)
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
