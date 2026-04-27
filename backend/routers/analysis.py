from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from services.analysis_dashboard import build_eco_index_payload, get_dashboard_bundle
from services.guideline_metrics import build_guideline_metrics


router = APIRouter(prefix="/api/analysis", tags=["综合分析"])


@router.get("/eco-index")
async def get_eco_index(db: AsyncSession = Depends(get_db)):
    return {"data": await build_eco_index_payload(db)}


@router.get("/guideline-metrics")
async def get_guideline_metrics(db: AsyncSession = Depends(get_db)):
    metrics = await build_guideline_metrics(db)
    return {"data": metrics}


@router.get("/dashboard")
async def get_analysis_dashboard(db: AsyncSession = Depends(get_db)):
    dashboard = await get_dashboard_bundle(
        db,
        ttl_seconds=settings.ANALYTICS_DASHBOARD_CACHE_SECONDS,
    )
    return {"data": dashboard}
