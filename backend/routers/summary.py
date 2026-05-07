"""综合概览接口 - 大屏首屏所需数据的一次性汇总."""
import asyncio
import logging
import time
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import get_token
from config import settings
from database import get_db
from models import (
    CollectLog,
    InsectRecord,
    RainfallRecord,
    RunoffRecord,
    SporeRecord,
    WaterQualityRecord,
)
from services.weather_support import get_weather_support
from services.water_quality_support import (
    get_latest_water_quality_record,
    resolve_water_quality_codes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summary", tags=["综合概览"])

_device_status_cache: dict[str, object] = {
    "value": None,
    "expires_at": 0.0,
}
_device_status_lock = asyncio.Lock()

RUNOFF_DEVICES = [
    ("16132920", "杧果林径流监测系统1号"),
    ("16132921", "橡胶林径流监测系统1号"),
    ("16132922", "次生林径流监测系统"),
    ("16132923", "杧果林径流监测系统2号"),
    ("16132924", "橡胶林径流监测系统2号"),
    ("16132925", "槟榔林径流监测系统"),
]


def _probe_time_range(minutes_back: int = 10) -> str:
    end = datetime.now()
    start = end - timedelta(minutes=minutes_back)
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"


async def _get_latest_by_code(db: AsyncSession, model, code: str):
    result = await db.execute(
        select(model).where(model.device_code == code).order_by(desc(model.collection_time)).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_latest_non_null_field_by_code(
    db: AsyncSession,
    model,
    code: str,
    field_name: str,
):
    field = getattr(model, field_name)
    result = await db.execute(
        select(field)
        .where(model.device_code == code, field.is_not(None))
        .order_by(desc(model.collection_time))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_non_empty_image(db: AsyncSession, model) -> str | None:
    result = await db.execute(
        select(model.image_url)
        .where(model.image_url.is_not(None), model.image_url != "")
        .order_by(desc(model.collection_time))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _probe_device_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    timeout = httpx.Timeout(8.0, connect=5.0)
    whxph_base_url = settings.WHXPH_BASE_URL.rstrip("/")

    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        async def probe(name: str, url: str, *, params: dict | None = None, headers: dict | None = None):
            try:
                resp = await client.get(url, params=params, headers=headers)
                statuses[name] = "online" if resp.status_code == 200 else "offline"
            except Exception as exc:
                logger.warning("Device probe failed for %s: %s", name, exc)
                statuses[name] = "offline"

        platform_headers = None
        try:
            token = await get_token()
            platform_headers = {"Authorization": token}
        except Exception as exc:
            logger.warning("Failed to fetch platform token for device probes: %s", exc)
            statuses["insect"] = "offline"
            statuses["spore"] = "offline"

        tasks = []
        if platform_headers:
            bugwarm_url = f"{settings.PLATFORM_BASE_URL}/http/monitor/getBugWarmByCode"
            probe_range = _probe_time_range()
            tasks.extend([
                probe(
                    "insect",
                    bugwarm_url,
                    params={"code": settings.INSECT_CODE, "collectionTime": probe_range},
                    headers=platform_headers,
                ),
                probe(
                    "spore",
                    bugwarm_url,
                    params={"code": settings.SPORE_CODE, "collectionTime": probe_range},
                    headers=platform_headers,
                ),
            ])

        water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
        tasks.append(probe("water", f"{whxph_base_url}/data-n/{water_code}"))

        for code in [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]:
            tasks.append(probe(f"rain_{code}", f"{whxph_base_url}/data-n/{code}"))

        for code in [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]:
            tasks.append(probe(f"runoff_{code}", f"{whxph_base_url}/data-n/{code}"))

        if tasks:
            await asyncio.gather(*tasks)

    return statuses


async def _get_device_statuses() -> dict[str, str]:
    now = time.monotonic()
    cached_value = _device_status_cache["value"]
    expires_at = float(_device_status_cache["expires_at"])
    if isinstance(cached_value, dict) and now < expires_at:
        return dict(cached_value)

    async with _device_status_lock:
        now = time.monotonic()
        cached_value = _device_status_cache["value"]
        expires_at = float(_device_status_cache["expires_at"])
        if isinstance(cached_value, dict) and now < expires_at:
            return dict(cached_value)

        statuses = await _probe_device_statuses()
        ttl = max(5, int(settings.DEVICE_STATUS_CACHE_SECONDS))
        _device_status_cache["value"] = dict(statuses)
        _device_status_cache["expires_at"] = now + ttl
        return dict(statuses)


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """大屏首屏所有关键指标一次性返回"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    device_statuses = await _get_device_statuses()
    weather_support = await get_weather_support()

    insect_res = await db.execute(
        select(InsectRecord).order_by(desc(InsectRecord.collection_time)).limit(1)
    )
    insect = insect_res.scalar_one_or_none()

    spore_res = await db.execute(
        select(SporeRecord).order_by(desc(SporeRecord.collection_time)).limit(1)
    )
    spore = spore_res.scalar_one_or_none()

    today_insect_res = await db.execute(
        select(func.sum(InsectRecord.total_count)).where(InsectRecord.collection_time >= today)
    )
    today_insect_total = today_insect_res.scalar() or 0
    yesterday_insect_res = await db.execute(
        select(func.sum(InsectRecord.total_count)).where(
            InsectRecord.collection_time >= yesterday,
            InsectRecord.collection_time < today,
        )
    )
    yesterday_insect_total = yesterday_insect_res.scalar() or 0

    week_ago = datetime.now() - timedelta(days=7)
    trend_res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= week_ago)
        .order_by(InsectRecord.collection_time)
    )
    trend_records = trend_res.scalars().all()
    daily_trend: dict[str, int] = {}
    for record in trend_records:
        day = record.collection_time.strftime("%m-%d")
        daily_trend[day] = daily_trend.get(day, 0) + record.total_count

    log_res = await db.execute(
        select(CollectLog).order_by(desc(CollectLog.created_at)).limit(5)
    )
    logs = log_res.scalars().all()

    runoff_data = {}
    runoff_codes = [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]
    for code in runoff_codes:
        record = await _get_latest_by_code(db, RunoffRecord, code)
        if not record:
            continue
        liquid_pressure = record.liquid_pressure
        if liquid_pressure is None:
            liquid_pressure = await _get_latest_non_null_field_by_code(
                db, RunoffRecord, code, "liquid_pressure"
            )
        runoff_data[code] = {
            "device_code": code,
            "flow_speed": record.flow_speed,
            "flow_rate": record.flow_rate,
            "total_flow": record.total_flow,
            "water_level": record.water_level,
            "sand_content": record.sand_content,
            "liquid_pressure": liquid_pressure,
            "runoff": record.runoff,
            "rainfall": record.rainfall,
            "updated_at": record.collection_time.isoformat(),
            "status": device_statuses.get(f"runoff_{code}", "offline"),
        }

    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    active_water_codes = await resolve_water_quality_codes(db, preferred_code=configured_water_code)
    water_record = await get_latest_water_quality_record(db, active_water_codes)
    water_quality = {
        "device_code": water_record.device_code,
        "nh4n": water_record.ammonia_nitrogen,
        "tp": water_record.total_phosphorus,
        "tn": water_record.total_nitrogen,
        "permanganate": water_record.permanganate_index,
        "updated_at": water_record.collection_time.isoformat(),
        "status": device_statuses.get("water", "offline"),
    } if water_record else None

    rain_data = {}
    rain_codes = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    for code in rain_codes:
        record = await _get_latest_by_code(db, RainfallRecord, code)
        if not record:
            continue
        rain_data[code] = {
            "rainfall": record.rainfall,
            "updated_at": record.collection_time.isoformat(),
            "status": device_statuses.get(f"rain_{code}", "offline"),
        }

    insect_image_url = insect.image_url if insect and insect.image_url else await _latest_non_empty_image(db, InsectRecord)
    spore_image_url = spore.image_url if spore and spore.image_url else await _latest_non_empty_image(db, SporeRecord)

    return {
        "data": {
            "insect": {
                "total_today": int(today_insect_total),
                "total_yesterday": int(yesterday_insect_total),
                "latest_count": insect.total_count if insect else None,
                "top_species": sorted(
                    (insect.species_data or {}).items(), key=lambda item: item[1], reverse=True
                )[:5] if insect else [],
                "image_url": insect_image_url,
                "updated_at": insect.collection_time.isoformat() if insect else None,
                "status": device_statuses.get("insect", "offline"),
            },
            "spore": {
                "latest_count": spore.total_count if spore else None,
                "image_url": spore_image_url,
                "updated_at": spore.collection_time.isoformat() if spore else None,
                "status": device_statuses.get("spore", "offline"),
            },
            "insect_trend": [{"date": key, "count": value} for key, value in daily_trend.items()],
            "collect_logs": [
                {
                    "task": log.task_name,
                    "status": log.status,
                    "count": log.records_count,
                    "time": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "runoff_stations": runoff_data,
            "water_quality": water_quality,
            "rain_gauges": rain_data,
            "weather_support": weather_support,
        }
    }


@router.get("/device-status")
async def get_device_status(db: AsyncSession = Depends(get_db)):
    """设备在线状态，以设备接口 HTTP 200 为在线依据。"""
    device_statuses = await _get_device_statuses()

    async def last_time(model, code: str | None = None):
        query = select(model.collection_time).order_by(desc(model.collection_time)).limit(1)
        if code is not None:
            query = query.where(model.device_code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    insect_time = await last_time(InsectRecord)
    spore_time = await last_time(SporeRecord)
    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    active_water_codes = await resolve_water_quality_codes(db, preferred_code=configured_water_code)
    water_time = None
    if active_water_codes:
        water_latest = await get_latest_water_quality_record(db, active_water_codes)
        water_time = water_latest.collection_time if water_latest else None

    devices = [
        {
            "name": "智能虫情测报灯",
            "code": "insect",
            "status": device_statuses.get("insect", "offline"),
            "last_data": insect_time.isoformat() if insect_time else None,
        },
        {
            "name": "孢子捕捉仪",
            "code": "spore",
            "status": device_statuses.get("spore", "offline"),
            "last_data": spore_time.isoformat() if spore_time else None,
        },
        {
            "name": "面源污染监测站",
            "code": "water",
            "status": device_statuses.get("water", "offline"),
            "last_data": water_time.isoformat() if water_time else None,
        },
    ]

    rain_codes = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    for index, code in enumerate(rain_codes, 1):
        record_time = await last_time(RainfallRecord, code)
        devices.append({
            "name": f"4G雨量计{index}号",
            "code": f"rain_{code}",
            "status": device_statuses.get(f"rain_{code}", "offline"),
            "last_data": record_time.isoformat() if record_time else None,
        })

    for code, name in RUNOFF_DEVICES:
        record_time = await last_time(RunoffRecord, code)
        devices.append({
            "name": name,
            "code": f"runoff_{code}",
            "status": device_statuses.get(f"runoff_{code}", "offline"),
            "last_data": record_time.isoformat() if record_time else None,
        })

    return {"data": devices}
