from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from services.analysis_dashboard import build_eco_index_payload, get_dashboard_bundle
from services.guideline_metrics import build_guideline_metrics


router = APIRouter(prefix="/api/analysis", tags=["综合分析"])

_analysis_runtime_cache: dict[str, dict[str, object]] = {
    "value": {},
    "expires_at": {},
}
_analysis_runtime_locks: dict[str, asyncio.Lock] = {}


async def _get_analysis_cached_payload(cache_name: str, loader):
    now = time.monotonic()
    expires_at = float(_analysis_runtime_cache["expires_at"].get(cache_name, 0.0))
    if cache_name in _analysis_runtime_cache["value"] and now < expires_at:
        return _analysis_runtime_cache["value"][cache_name]

    lock = _analysis_runtime_locks.setdefault(cache_name, asyncio.Lock())
    async with lock:
        now = time.monotonic()
        expires_at = float(_analysis_runtime_cache["expires_at"].get(cache_name, 0.0))
        if cache_name in _analysis_runtime_cache["value"] and now < expires_at:
            return _analysis_runtime_cache["value"][cache_name]

        payload = await loader()
        ttl = max(1, int(settings.ANALYSIS_RUNTIME_CACHE_SECONDS))
        _analysis_runtime_cache["value"][cache_name] = payload
        _analysis_runtime_cache["expires_at"][cache_name] = now + ttl
        return payload


@router.get("/eco-index")
async def get_eco_index(db: AsyncSession = Depends(get_db)):
    payload = await _get_analysis_cached_payload("eco-index", lambda: build_eco_index_payload(db))
    return {"data": payload}


@router.get("/guideline-metrics")
async def get_guideline_metrics(db: AsyncSession = Depends(get_db)):
    metrics = await _get_analysis_cached_payload("guideline-metrics", lambda: build_guideline_metrics(db))
    return {"data": metrics}


@router.get("/dashboard")
async def get_analysis_dashboard(
    force_refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    dashboard = await get_dashboard_bundle(
        db,
        force_refresh=force_refresh,
        ttl_seconds=settings.ANALYTICS_DASHBOARD_CACHE_SECONDS,
    )
    return {"data": dashboard}
