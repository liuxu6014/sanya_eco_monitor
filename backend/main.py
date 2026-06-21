import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from logging_setup import build_logging_config, configure_logging
from auth import auth_role_from_cookie, is_auth_enabled, is_valid_auth_cookie
from database import init_db
from scheduler import setup_scheduler, _run_all_collectors
from routers import (
    insect as insect_router,
    sensor as sensor_router,
    summary as summary_router,
    report as report_router,
    analysis as analysis_router,
    auth as auth_dev_router,
    maintenance as maintenance_router,
)
from config import settings

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized.")

    if settings.RUN_COLLECTORS_ON_STARTUP:
        try:
            await _run_all_collectors()
        except Exception as e:
            logger.warning(f"Initial collection failed (non-fatal): {e}")

    sched = setup_scheduler()
    sched.start()
    logger.info(f"Scheduler started (interval: {settings.COLLECT_INTERVAL_MINUTES} min)")

    yield

    # Shutdown
    sched.shutdown()


app = FastAPI(
    title=settings.APP_TITLE,
    version="1.0.0",
    lifespan=lifespan,
)

def _cors_allow_origins() -> list[str]:
    configured = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
    # 未配置时仅放行本地开发端口；生产经 nginx 同源代理无需跨域。
    return configured or [
        "http://localhost:5173",
        "http://localhost:5175",
        "http://localhost:5188",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/logout",
}


@app.middleware("http")
async def require_platform_password(request: Request, call_next):
    path = request.url.path
    if (
        request.method == "OPTIONS"
        or not path.startswith("/api")
        or path in AUTH_EXEMPT_PATHS
        or not is_auth_enabled()
    ):
        return await call_next(request)

    cookie_value = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not is_valid_auth_cookie(cookie_value):
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    return await call_next(request)


app.include_router(auth_dev_router.router)
app.include_router(insect_router.router)
app.include_router(sensor_router.router)
app.include_router(summary_router.router)
app.include_router(report_router.router)
app.include_router(analysis_router.router)
app.include_router(maintenance_router.router)


def _require_admin(request: Request) -> JSONResponse | None:
    if auth_role_from_cookie(request.cookies.get(settings.AUTH_COOKIE_NAME)) == "admin":
        return None
    return JSONResponse(status_code=403, content={"detail": "Admin role required"})


@app.get("/api/health")
async def health():
    return {"status": "ok", "title": settings.APP_TITLE}


@app.get("/api/report/ai-placeholder")
async def ai_report_placeholder():
    return {
        "status": "pending",
        "message": "AI分析功能已预留，配置大模型API Key后自动启用",
        "model": "claude-sonnet-4-6"
    }


@app.post("/api/collect/trigger")
async def trigger_collect(request: Request):
    """手动触发一次数据采集（调试用）"""
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    await _run_all_collectors()
    return {"status": "ok", "message": "采集完成"}


@app.get("/api/debug/settings")
async def debug_settings(request: Request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    return {
        "SENSOR_BASE_URL": settings.SENSOR_BASE_URL,
        "PLATFORM_BASE_URL": settings.PLATFORM_BASE_URL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        access_log=True,
        log_config=build_logging_config(),
    )
