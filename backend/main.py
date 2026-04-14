import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from auth import is_auth_enabled, is_valid_auth_cookie
from database import init_db
from scheduler import setup_scheduler, _run_all_collectors
from routers import insect, sensor, summary, report, analysis, auth
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized.")

    # Initial data collection on startup
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


app.include_router(auth.router)
app.include_router(insect.router)
app.include_router(sensor.router)
app.include_router(summary.router)
app.include_router(report.router)
app.include_router(analysis.router)


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
async def trigger_collect():
    """手动触发一次数据采集（调试用）"""
    await _run_all_collectors()
    return {"status": "ok", "message": "采集完成"}


@app.get("/api/debug/settings")
async def debug_settings():
    return {
        "SENSOR_BASE_URL": settings.SENSOR_BASE_URL,
        "PLATFORM_BASE_URL": settings.PLATFORM_BASE_URL,
    }
