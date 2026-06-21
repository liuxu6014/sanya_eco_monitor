import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from auth import auth_role_from_cookie, clear_auth_cookie, is_auth_enabled, is_valid_auth_cookie, set_auth_cookie
from config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
async def auth_status(request: Request):
    role = auth_role_from_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME))
    return {
        "authenticated": is_valid_auth_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME)),
        "enabled": is_auth_enabled(),
        "role": role,
    }


@router.post("/login")
async def auth_login(payload: LoginRequest, response: Response):
    if not is_auth_enabled():
        return {"status": "ok", "authenticated": True, "enabled": False}

    # secrets.compare_digest 比较 str 时不支持非 ASCII 字符，密码可能含中文，统一按 UTF-8 字节比较。
    def _password_matches(candidate: str, expected: str) -> bool:
        return secrets.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))

    role = None
    if _password_matches(payload.password, settings.ACCESS_PASSWORD):
        role = "admin"
    elif settings.LEADER_ACCESS_PASSWORD.strip() and _password_matches(
        payload.password,
        settings.LEADER_ACCESS_PASSWORD,
    ):
        role = "leader"

    if not role:
        raise HTTPException(status_code=401, detail="密码错误")

    set_auth_cookie(response, role=role)
    return {"status": "ok", "authenticated": True, "enabled": True, "role": role}


@router.post("/logout")
async def auth_logout(request: Request, response: Response):
    clear_auth_cookie(
        response,
        cookie_value=request.cookies.get(settings.AUTH_COOKIE_NAME),
    )
    return {"status": "ok"}
