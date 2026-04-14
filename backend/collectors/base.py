"""
Base HTTP client with JWT token caching and auto-refresh.
Token expires in 30 minutes per platform docs.
"""
import time
import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)

_token_cache: dict = {"token": None, "expires_at": 0}


async def get_token() -> str:
    """Return cached token or fetch a new one if expired/missing."""
    now = time.time()
    # Refresh 60 seconds before expiry
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    logger.info("Fetching new platform token...")
    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        # PLATFORM_BASE_URL must be the API root, e.g. https://zhnlkj.com/iotSmasrt
        # Do not include /login in the env value, because the login path is appended here.
        resp = await client.post(
            f"{settings.PLATFORM_BASE_URL}/login",
            json={"username": settings.PLATFORM_USERNAME, "password": settings.PLATFORM_PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 200:
        raise RuntimeError(f"Login failed: {data}")

    token = data["data"]["token"]
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 30 * 60  # 30 minutes
    logger.info("Platform token obtained successfully.")
    return token


async def platform_get(path: str, params: dict | None = None) -> dict:
    """Authenticated GET request to the platform API."""
    token = await get_token()
    async with httpx.AsyncClient(verify=False, timeout=20) as client:
        resp = await client.get(
            f"{settings.PLATFORM_BASE_URL}{path}",
            params=params,
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return resp.json()
