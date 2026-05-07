from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import InsectRecord, RunoffRecord, SporeRecord, WaterQualityRecord
from routers.insect import get_combined_trend, get_species_heatmap
from routers.sensor import get_runoff_daily, get_wq_daily
from services.guideline_metrics import build_guideline_metrics
from services.water_quality_support import get_latest_water_quality_record, resolve_water_quality_codes

_dashboard_cache: dict[str, Any] = {"value": None, "expires_at": 0.0}
_dashboard_lock = asyncio.Lock()


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _avg(values: list[float | None], digits: int = 2) -> float:
    clean = [value for value in values if value is not None]
    if not clean:
        return 0.0
    return round(sum(clean) / len(clean), digits)


async def build_eco_index_payload(db: AsyncSession) -> dict[str, Any]:
    now = datetime.now()
    since_7d = now - timedelta(days=7)
    since_24h = now - timedelta(hours=24)

    insect_result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= since_7d)
        .order_by(desc(InsectRecord.collection_time))
    )
    insects = insect_result.scalars().all()
    total_insects = sum(record.total_count for record in insects)
    avg_insects = round(total_insects / len(insects), 1) if insects else 0.0

    spore_result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= since_7d)
        .order_by(desc(SporeRecord.collection_time))
    )
    spores = spore_result.scalars().all()
    total_spores = sum(record.total_count for record in spores)
    avg_spores = round(total_spores / len(spores), 1) if spores else 0.0

    runoff_result = await db.execute(
        select(RunoffRecord)
        .where(RunoffRecord.collection_time >= since_24h)
        .order_by(desc(RunoffRecord.collection_time))
    )
    runoff_records = runoff_result.scalars().all()
    avg_flow = _avg([record.flow_rate for record in runoff_records])
    avg_sand = _avg([record.sand_content for record in runoff_records])
    avg_runoff = _avg([record.runoff for record in runoff_records])
    avg_level = _avg([record.water_level for record in runoff_records])

    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    active_water_codes = await resolve_water_quality_codes(db, preferred_code=configured_water_code)
    water_record = await get_latest_water_quality_record(db, active_water_codes)

    insect_score = _clamp(avg_insects / 2.5, 0, 55)
    spore_score = _clamp(avg_spores / 2.0, 0, 45)
    pest_risk = round(insect_score + spore_score)

    insect_activity = _clamp(avg_insects / 2.0, 0, 60)
    spore_activity = _clamp(100 - avg_spores / 2.5, 0, 40)
    bio_activity = round(insect_activity + spore_activity)

    flow_penalty = _clamp(avg_flow * 30, 0, 35)
    sand_penalty = _clamp(avg_sand * 120, 0, 35)
    runoff_penalty = _clamp(avg_runoff * 25, 0, 20)
    level_penalty = _clamp(avg_level * 20, 0, 10)
    hydrology_health = round(100 - flow_penalty - sand_penalty - runoff_penalty - level_penalty)

    erosion_val = avg_flow * 35 + avg_sand * 120 + avg_runoff * 20
    erosion_index = round(_clamp(erosion_val, 0, 100))

    if water_record:
        p_permanganate = _clamp((water_record.permanganate_index or 0) / 15 * 100, 0, 100)
        p_nh4 = _clamp((water_record.ammonia_nitrogen or 0) / 2.0 * 100, 0, 100)
        p_tp = _clamp((water_record.total_phosphorus or 0) / 0.4 * 100, 0, 100)
        p_tn = _clamp((water_record.total_nitrogen or 0) / 2.0 * 100, 0, 100)
        pollution_index = round(p_permanganate * 0.3 + p_nh4 * 0.3 + p_tp * 0.2 + p_tn * 0.2)
    else:
        pollution_index = 0

    eco_health = round(
        bio_activity * 0.35
        + (100 - pest_risk) * 0.25
        + hydrology_health * 0.2
        + (100 - erosion_index) * 0.15
        + (100 - pollution_index) * 0.1
    )

    alerts: list[dict[str, str]] = []
    if pest_risk >= 70:
        alerts.append({"level": "danger", "msg": "病虫害风险极高，建议立即开展田间复核。"})
    elif pest_risk >= 45:
        alerts.append({"level": "warning", "msg": "病虫害风险偏高，建议提升监测频率。"})

    if hydrology_health <= 35:
        alerts.append({"level": "danger", "msg": "径流波动偏大，存在较高水土流失风险。"})
    elif hydrology_health <= 60:
        alerts.append({"level": "warning", "msg": "水文状态一般，建议持续关注径流与含沙变化。"})

    if pollution_index >= 70:
        alerts.append({"level": "danger", "msg": "面源污染负荷偏高，建议排查污染输入。"})
    elif pollution_index >= 45:
        alerts.append({"level": "warning", "msg": "水环境负荷上升，建议加强水质巡检。"})

    if bio_activity >= 80:
        alerts.append({"level": "info", "msg": "生物监测活跃度较高，群落演替信号明显。"})
    elif bio_activity <= 35:
        alerts.append({"level": "warning", "msg": "生物活跃度偏低，建议结合现场调查复核。"})

    if not alerts:
        alerts.append({"level": "info", "msg": "各项指标稳定，生态系统运行良好。"})

    return {
        "pest_risk": pest_risk,
        "bio_activity": bio_activity,
        "hydrology_health": hydrology_health,
        "erosion_risk": erosion_index,
        "pollution_load": pollution_index,
        "eco_health": eco_health,
        "alerts": alerts,
        "computed_at": now.isoformat(),
        "meta": {
            "insect_records_7d": len(insects),
            "spore_records_7d": len(spores),
            "runoff_records_24h": len(runoff_records),
            "avg_insects_7d": avg_insects,
            "avg_spores_7d": avg_spores,
            "avg_flow_rate_24h": avg_flow,
            "avg_runoff_24h": avg_runoff,
            "avg_sand_content_24h": avg_sand,
            "avg_water_level_24h": avg_level,
        },
    }


async def _fetch_dashboard_bundle(db: AsyncSession) -> dict[str, Any]:
    eco_index = await build_eco_index_payload(db)
    guideline_metrics = await build_guideline_metrics(db)
    water_quality_daily = await get_wq_daily(days=30, db=db)
    runoff_daily = await get_runoff_daily(days=30, db=db)
    combined_trend = await get_combined_trend(days=30, db=db)
    insect_heatmap = await get_species_heatmap(days=14, db=db)

    return {
        "eco_index": eco_index,
        "guideline_metrics": guideline_metrics,
        "water_quality_daily": water_quality_daily.get("data", []),
        "runoff_daily": runoff_daily.get("data", []),
        "combined_trend": combined_trend.get("data", []),
        "insect_heatmap": insect_heatmap.get("data", {}),
        "generated_at": datetime.now().isoformat(),
    }


async def get_dashboard_bundle(
    db: AsyncSession,
    *,
    force_refresh: bool = False,
    ttl_seconds: int = 60,
) -> dict[str, Any]:
    if force_refresh:
        async with _dashboard_lock:
            payload = await _fetch_dashboard_bundle(db)
            _dashboard_cache["value"] = payload
            _dashboard_cache["expires_at"] = time.monotonic() + max(1, ttl_seconds)
            return payload

    now = time.monotonic()
    cached_value = _dashboard_cache["value"]
    expires_at = float(_dashboard_cache["expires_at"])
    if isinstance(cached_value, dict) and now < expires_at:
        return cached_value

    async with _dashboard_lock:
        now = time.monotonic()
        cached_value = _dashboard_cache["value"]
        expires_at = float(_dashboard_cache["expires_at"])
        if isinstance(cached_value, dict) and now < expires_at:
            return cached_value

        payload = await _fetch_dashboard_bundle(db)
        _dashboard_cache["value"] = payload
        _dashboard_cache["expires_at"] = now + max(1, ttl_seconds)
        return payload
