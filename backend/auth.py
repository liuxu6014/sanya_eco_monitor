import hashlib
import secrets

from fastapi import Response

from config import settings


def is_auth_enabled() -> bool:
    return bool(settings.ACCESS_PASSWORD.strip())


def build_auth_token() -> str:
    token_seed = f"{settings.ACCESS_PASSWORD}|{settings.AUTH_COOKIE_NAME}|platform-access"
    return hashlib.sha256(token_seed.encode("utf-8")).hexdigest()


def build_leader_auth_token() -> str:
    token_seed = f"{settings.LEADER_ACCESS_PASSWORD}|{settings.AUTH_COOKIE_NAME}|leader-access"
    return hashlib.sha256(token_seed.encode("utf-8")).hexdigest()


def is_valid_auth_cookie(cookie_value: str | None) -> bool:
    if not is_auth_enabled():
        return True
    if not cookie_value:
        return False
    return secrets.compare_digest(cookie_value, build_auth_token()) or is_leader_auth_cookie(cookie_value)


def is_admin_auth_cookie(cookie_value: str | None) -> bool:
    if not is_auth_enabled():
        return True
    if not cookie_value:
        return False
    return secrets.compare_digest(cookie_value, build_auth_token())


def is_leader_auth_enabled() -> bool:
    return bool(settings.LEADER_ACCESS_PASSWORD.strip())


def is_leader_auth_cookie(cookie_value: str | None) -> bool:
    if not is_leader_auth_enabled() or not cookie_value:
        return False
    return secrets.compare_digest(cookie_value, build_leader_auth_token())


def auth_role_from_cookie(cookie_value: str | None) -> str | None:
    if is_admin_auth_cookie(cookie_value):
        return "admin"
    if is_leader_auth_cookie(cookie_value):
        return "leader"
    return None


def set_auth_cookie(response: Response, *, role: str = "admin") -> None:
    value = build_leader_auth_token() if role == "leader" else build_auth_token()
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=value,
        max_age=settings.AUTH_MAX_AGE_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )
