import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from auth import clear_auth_cookie, is_auth_enabled, is_valid_auth_cookie, set_auth_cookie
from config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
async def auth_status(request: Request):
    return {
        "authenticated": is_valid_auth_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME)),
        "enabled": is_auth_enabled(),
    }


@router.post("/login")
async def auth_login(payload: LoginRequest, response: Response):
    if not is_auth_enabled():
        return {"status": "ok", "authenticated": True, "enabled": False}

    if not secrets.compare_digest(payload.password, settings.ACCESS_PASSWORD):
        raise HTTPException(status_code=401, detail="密码错误")

    set_auth_cookie(response)
    return {"status": "ok", "authenticated": True, "enabled": True}


@router.post("/logout")
async def auth_logout(response: Response):
    clear_auth_cookie(response)
    return {"status": "ok"}
