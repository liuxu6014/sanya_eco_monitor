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
from database import AsyncSessionLocal, get_db
from models import (
    CollectLog,
    InsectRecord,
    RainfallRecord,
    RunoffRecord,
    SporeRecord,
    WaterQualityRecord,
)
from services.anomaly_flags import build_anomaly_summary, flag_numeric_anomalies
from services.image_quality import is_probably_black_image
from services.rainfall_aggregation import aggregate_rainfall_daily
from services.weather_support import get_weather_support
from services.water_quality_support import (
    get_latest_water_quality_record,
    resolve_water_quality_codes,
    water_metric_value,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summary", tags=["综合概览"])

_device_status_cache: dict[str, object] = {
    "value": None,
    "expires_at": 0.0,
    "refresh_task": None,
}
_overview_cache: dict[str, object] = {
    "value": None,
    "expires_at": 0.0,
    "refresh_task": None,
}
_device_status_lock = asyncio.Lock()
_overview_lock = asyncio.Lock()

RUNOFF_DEVICES = [
    ("16132920", "橡胶林径流监测系统1号"),
    ("16132921", "次生林径流监测系统"),
    ("16132922", "芒果林径流监测系统1号"),
    ("16132923", "槟榔林径流监测系统"),
    ("16132924", "橡胶林径流监测系统2号"),
    ("16132925", "芒果林径流监测系统2号"),
]

RUNOFF_LATEST_ANOMALY_RULES = {
    "runoff": {"min": 0, "max": 10, "label": "径流"},
    "sand_content": {"min": 0, "max": 1, "label": "含沙量"},
    "flow_rate": {"min": 0, "max": 100, "label": "流量"},
    "flow_speed": {"min": 0, "max": 100, "label": "流速"},
    "water_level": {"min": 0, "max": 100, "label": "水位"},
    "liquid_pressure": {"min": 0, "max": 100, "label": "液位压力"},
    "rainfall": {"min": 0, "max": 100, "label": "降雨量"},
}

DEVICE_STATUS_STALE_THRESHOLDS = {
    "water": timedelta(hours=2),
    "rain": timedelta(minutes=max(15, settings.COLLECT_INTERVAL_MINUTES * 3)),
    "runoff": timedelta(minutes=max(15, settings.COLLECT_INTERVAL_MINUTES * 3)),
}

DEFAULT_RAIN_GAUGE_CODES = ["16132920", "16132921", "16132922"]

INSECT_DEVICE_META = {
    "id": "insect",
    "type": "insect",
    "name": "智能虫情测报灯",
    "panel_name": "智能虫情测报灯",
    "short_name": "虫情测报灯",
    "map_name": "智能虫情测报灯",
    "map_lat": 18.349816,
    "map_lng": 109.362321,
    "map_color": "#ff1744",
    "map_label_offset": [-140, -120],
}

SPORE_DEVICE_META = {
    "id": "spore",
    "type": "spore",
    "name": "孢子捕捉仪",
    "panel_name": "孢子捕捉仪",
    "short_name": "孢子捕捉仪",
    "map_name": "孢子捕捉仪",
    "map_lat": 18.349816,
    "map_lng": 109.362321,
    "map_color": "#d500f9",
    "map_label_offset": [-160, -80],
}

WATER_DEVICE_META_BASE = {
    "id": "water",
    "type": "water",
    "name": "面源污染监测站",
    "panel_name": "面源污染监测站",
    "short_name": "面源水质站",
    "map_name": "面源污染监测站",
    "map_lat": 18.314145,
    "map_lng": 109.463094,
    "map_color": "#ffd600",
    "map_label_offset": [140, -100],
}

RUNOFF_DEVICE_META_BY_CODE = {
    "16132920": {
        "id": "runoff_16132920",
        "type": "runoff",
        "name": "橡胶林1监测点",
        "panel_name": "橡胶林1监测点",
        "short_name": "橡胶林径流点 1",
        "map_name": "橡胶林径流监测系统1号",
        "map_lat": 18.3640213,
        "map_lng": 109.4821167,
        "map_color": "#ff6d00",
        "map_label_offset": [180, 80],
    },
    "16132921": {
        "id": "runoff_16132921",
        "type": "runoff",
        "name": "次生林监测点",
        "panel_name": "次生林监测点",
        "short_name": "次生林径流点",
        "map_name": "次生林径流监测系统",
        "map_lat": 18.3628883,
        "map_lng": 109.4733582,
        "map_color": "#aeea00",
        "map_label_offset": [-160, 140],
    },
    "16132922": {
        "id": "runoff_16132922",
        "type": "runoff",
        "name": "芒果林1监测点",
        "panel_name": "芒果林1监测点",
        "short_name": "芒果林径流点 1",
        "map_name": "芒果林径流监测系统1号",
        "map_lat": 18.3940544,
        "map_lng": 109.4813004,
        "map_color": "#1de9b6",
        "map_label_offset": [120, -100],
    },
    "16132923": {
        "id": "runoff_16132923",
        "type": "runoff",
        "name": "槟榔林监测点",
        "panel_name": "槟榔林监测点",
        "short_name": "槟榔林径流点",
        "map_name": "槟榔林径流监测系统",
        "map_lat": 18.3672924,
        "map_lng": 109.4803925,
        "map_color": "#ff6d00",
        "map_label_offset": [-180, -140],
    },
    "16132924": {
        "id": "runoff_16132924",
        "type": "runoff",
        "name": "橡胶林2监测点",
        "panel_name": "橡胶林2监测点",
        "short_name": "橡胶林径流点 2",
        "map_name": "橡胶林径流监测系统2号",
        "map_lat": 18.3700542,
        "map_lng": 109.4898224,
        "map_color": "#aeea00",
        "map_label_offset": [220, -60],
    },
    "16132925": {
        "id": "runoff_16132925",
        "type": "runoff",
        "name": "芒果林2监测点",
        "panel_name": "芒果林2监测点",
        "short_name": "芒果林径流点 2",
        "map_name": "芒果林径流监测系统2号",
        "map_lat": 18.3916378,
        "map_lng": 109.4681549,
        "map_color": "#ff4081",
        "map_label_offset": [-100, -160],
    },
}

RAIN_GAUGE_META_BY_CODE = {
    "16132920": {
        "id": "rain_16132920",
        "type": "rain",
        "name": "橡胶林雨量站",
        "panel_name": "橡胶林站 (4G)",
        "short_name": "橡胶林雨量站",
        "map_name": "4G雨量计1号",
        "map_lat": 18.3640213,
        "map_lng": 109.4821167,
        "map_color": "#2979ff",
        "map_label_offset": [100, 160],
    },
    "16132921": {
        "id": "rain_16132921",
        "type": "rain",
        "name": "次生林雨量站",
        "panel_name": "次生林站 (4G)",
        "short_name": "次生林雨量站",
        "map_name": "4G雨量计2号",
        "map_lat": 18.3628883,
        "map_lng": 109.4733582,
        "map_color": "#2979ff",
        "map_label_offset": [-200, 0],
    },
    "16132922": {
        "id": "rain_16132922",
        "type": "rain",
        "name": "芒果林雨量站",
        "panel_name": "芒果林站 (4G)",
        "short_name": "芒果林雨量站",
        "map_name": "4G雨量计3号",
        "map_lat": 18.3940544,
        "map_lng": 109.4813004,
        "map_color": "#2979ff",
        "map_label_offset": [240, -20],
    },
}


def _is_synthetic_record(record) -> bool:
    return bool(record and isinstance(record.raw_data, dict) and record.raw_data.get("synthetic") is True)


def _resolve_device_health_status(
    *,
    probed_status: str | None,
    last_data_time: datetime | None,
    stale_after: timedelta,
    now: datetime | None = None,
) -> str:
    if probed_status != "online":
        return "offline"

    if last_data_time is None:
        return "timeout"

    current_time = now or datetime.now()
    if current_time - last_data_time > stale_after:
        return "timeout"

    return "online"


def _configured_rain_gauge_codes() -> list[str]:
    codes = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    return codes or list(DEFAULT_RAIN_GAUGE_CODES)


def _configured_runoff_codes() -> list[str]:
    return [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]


def _build_runoff_rain_mapping(device_meta: dict) -> dict[str, str]:
    rain_codes = {item.get("code") for item in (device_meta.get("rain_gauges") or []) if item.get("code")}
    runoff_codes = [item.get("code") for item in (device_meta.get("runoff_devices") or []) if item.get("code")]
    return {code: code for code in runoff_codes if code in rain_codes}


def _build_device_meta() -> dict:
    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    rain_codes = _configured_rain_gauge_codes()
    runoff_codes = _configured_runoff_codes()

    insect = {
        **INSECT_DEVICE_META,
        "code": settings.INSECT_CODE,
    }
    spore = {
        **SPORE_DEVICE_META,
        "code": settings.SPORE_CODE,
    }
    water = {
        **WATER_DEVICE_META_BASE,
        "code": configured_water_code,
    }

    rain_gauges = [
        {
            **RAIN_GAUGE_META_BY_CODE.get(
                code,
                {
                    "id": f"rain_{code}",
                    "type": "rain",
                    "name": f"{code}雨量站",
                    "panel_name": f"{code} 雨量站",
                    "short_name": f"{code}雨量站",
                    "map_name": f"{code}雨量站",
                    "map_lat": None,
                    "map_lng": None,
                    "map_color": "#2979ff",
                    "map_label_offset": [0, 0],
                },
            ),
            "code": code,
        }
        for code in rain_codes
    ]

    runoff_devices = [
        {
            **RUNOFF_DEVICE_META_BY_CODE.get(
                code,
                {
                    "id": f"runoff_{code}",
                    "type": "runoff",
                    "name": code,
                    "panel_name": code,
                    "short_name": code,
                    "map_name": code,
                    "map_lat": None,
                    "map_lng": None,
                    "map_color": "#38bdf8",
                    "map_label_offset": [0, 0],
                },
            ),
            "code": code,
        }
        for code in runoff_codes
    ]

    return {
        "insect": insect,
        "spore": spore,
        "water_quality": water,
        "rain_gauges": rain_gauges,
        "runoff_devices": runoff_devices,
    }


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


async def _get_latest_records_by_codes(db: AsyncSession, model, codes: list[str]) -> dict[str, object]:
    if not codes:
        return {}

    result = await db.execute(
        select(model)
        .where(model.device_code.in_(codes))
        .order_by(model.device_code, desc(model.collection_time))
    )
    latest: dict[str, object] = {}
    for record in result.scalars().all():
        code = getattr(record, "device_code", None)
        if code and code not in latest:
            latest[code] = record
    return latest


async def _get_latest_n_records_by_codes(
    db: AsyncSession,
    model,
    codes: list[str],
    *,
    limit: int,
) -> dict[str, list[object]]:
    if not codes:
        return {}

    result = await db.execute(
        select(model)
        .where(model.device_code.in_(codes))
        .order_by(model.device_code, desc(model.collection_time))
    )
    latest_records: dict[str, list[object]] = {code: [] for code in codes}
    for record in result.scalars().all():
        code = getattr(record, "device_code", None)
        if not code:
            continue
        records = latest_records.setdefault(code, [])
        if len(records) < limit:
            records.append(record)
    return latest_records


def _calculate_realtime_rainfall(records: list[object]) -> float | None:
    if len(records) < 10:
        return None

    latest = getattr(records[0], "rainfall", None)
    tenth = getattr(records[9], "rainfall", None)
    if latest is None or tenth is None:
        return None
    return max(0, latest - tenth)


async def _get_latest_non_null_fields_by_codes(
    db: AsyncSession,
    model,
    codes: list[str],
    field_name: str,
) -> dict[str, object]:
    if not codes:
        return {}

    field = getattr(model, field_name)
    result = await db.execute(
        select(model)
        .where(model.device_code.in_(codes), field.is_not(None))
        .order_by(model.device_code, desc(model.collection_time))
    )
    latest: dict[str, object] = {}
    for record in result.scalars().all():
        code = getattr(record, "device_code", None)
        if code and code not in latest:
            latest[code] = getattr(record, field_name)
    return latest


async def _get_records_since_by_codes(
    db: AsyncSession,
    model,
    codes: list[str],
    start_time: datetime,
) -> dict[str, list[object]]:
    if not codes:
        return {}

    result = await db.execute(
        select(model)
        .where(model.device_code.in_(codes), model.collection_time >= start_time)
        .order_by(model.device_code, model.collection_time)
    )
    grouped: dict[str, list[object]] = {code: [] for code in codes}
    for record in result.scalars().all():
        grouped.setdefault(record.device_code, []).append(record)
    return grouped


async def _get_latest_collection_times_by_codes(
    db: AsyncSession,
    model,
    codes: list[str],
) -> dict[str, datetime]:
    if not codes:
        return {}

    result = await db.execute(
        select(model.device_code, func.max(model.collection_time))
        .where(model.device_code.in_(codes))
        .group_by(model.device_code)
    )
    return {code: collected_at for code, collected_at in result.all() if code and collected_at}


async def _latest_non_empty_image(db: AsyncSession, model) -> str | None:
    result = await db.execute(
        select(model.image_url)
        .where(model.image_url.is_not(None), model.image_url != "")
        .order_by(desc(model.collection_time))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_valid_spore_image(db: AsyncSession, exclude_url: str | None = None) -> str | None:
    result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.image_url.is_not(None), SporeRecord.image_url != "")
        .order_by(desc(SporeRecord.collection_time))
        .limit(60)
    )
    for record in result.scalars().all():
        if _is_synthetic_record(record):
            continue
        if exclude_url and record.image_url == exclude_url:
            continue
        if record.image_url and not await is_probably_black_image(record.image_url):
            return record.image_url
    return None


async def _probe_device_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    timeout = httpx.Timeout(8.0, connect=5.0)
    whxph_base_url = settings.WHXPH_BASE_URL.rstrip("/")

    async with httpx.AsyncClient(verify=settings.HTTP_TLS_VERIFY, timeout=timeout) as client:
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

    if isinstance(cached_value, dict):
        _schedule_device_status_refresh()
        return dict(cached_value)

    async with _device_status_lock:
        now = time.monotonic()
        cached_value = _device_status_cache["value"]
        expires_at = float(_device_status_cache["expires_at"])
        if isinstance(cached_value, dict) and now < expires_at:
            return dict(cached_value)

        statuses = await _probe_device_statuses()
        _store_device_status_cache(statuses, now=now)
        return dict(statuses)


def _store_device_status_cache(statuses: dict[str, str], *, now: float | None = None) -> None:
    ttl = max(5, int(settings.DEVICE_STATUS_CACHE_SECONDS))
    base = time.monotonic() if now is None else now
    _device_status_cache["value"] = dict(statuses)
    _device_status_cache["expires_at"] = base + ttl


def _schedule_device_status_refresh() -> None:
    current_task = _device_status_cache.get("refresh_task")
    if current_task is not None and not current_task.done():
        return

    task = asyncio.create_task(_refresh_device_statuses())
    _device_status_cache["refresh_task"] = task
    task.add_done_callback(_clear_device_status_refresh_task)


async def _refresh_device_statuses() -> None:
    async with _device_status_lock:
        statuses = await _probe_device_statuses()
        _store_device_status_cache(statuses)


def _clear_device_status_refresh_task(task: asyncio.Task) -> None:
    current_task = _device_status_cache.get("refresh_task")
    if current_task is task:
        _device_status_cache["refresh_task"] = None

    try:
        task.result()
    except Exception as exc:
        logger.warning("Device status background refresh failed: %s", exc)


async def _build_overview_payload(db: AsyncSession):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    device_statuses = await _get_device_statuses()
    weather_support = await get_weather_support()
    device_meta = _build_device_meta()
    runoff_rain_mapping = _build_runoff_rain_mapping(device_meta)

    insect_res = await db.execute(
        select(InsectRecord).order_by(desc(InsectRecord.collection_time)).limit(30)
    )
    insect = next((item for item in insect_res.scalars().all() if not _is_synthetic_record(item)), None)

    spore_res = await db.execute(
        select(SporeRecord).order_by(desc(SporeRecord.collection_time)).limit(30)
    )
    spore = next((item for item in spore_res.scalars().all() if not _is_synthetic_record(item)), None)

    today_insect_res = await db.execute(
        select(InsectRecord).where(InsectRecord.collection_time >= today)
    )
    today_insect_total = sum(
        record.total_count for record in today_insect_res.scalars().all()
        if not _is_synthetic_record(record)
    )
    yesterday_insect_res = await db.execute(
        select(InsectRecord).where(
            InsectRecord.collection_time >= yesterday,
            InsectRecord.collection_time < today,
        )
    )
    yesterday_insect_total = sum(
        record.total_count for record in yesterday_insect_res.scalars().all()
        if not _is_synthetic_record(record)
    )

    week_ago = datetime.now() - timedelta(days=7)
    trend_res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= week_ago)
        .order_by(InsectRecord.collection_time)
    )
    trend_records = [record for record in trend_res.scalars().all() if not _is_synthetic_record(record)]
    daily_trend: dict[str, int] = {}
    for record in trend_records:
        day = record.collection_time.strftime("%m-%d")
        daily_trend[day] = daily_trend.get(day, 0) + record.total_count

    log_res = await db.execute(
        select(CollectLog).order_by(desc(CollectLog.created_at)).limit(5)
    )
    logs = log_res.scalars().all()

    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    active_water_codes = await resolve_water_quality_codes(db, preferred_code=configured_water_code)
    water_record = await get_latest_water_quality_record(db, active_water_codes)
    water_quality = {
        "device_code": water_record.device_code,
        "nh4n": water_record.ammonia_nitrogen,
        "tp": water_record.total_phosphorus,
        "tn": water_record.total_nitrogen,
        "permanganate": water_metric_value(water_record, "permanganate_index", "permanganate"),
        "updated_at": water_record.collection_time.isoformat(),
        "status": _resolve_device_health_status(
            probed_status=device_statuses.get("water", "offline"),
            last_data_time=water_record.collection_time,
            stale_after=DEVICE_STATUS_STALE_THRESHOLDS["water"],
        ),
    } if water_record else None

    rain_codes = _configured_rain_gauge_codes()
    rain_data = {}
    today_rainfall_by_code = {}
    latest_rain_records = await _get_latest_records_by_codes(db, RainfallRecord, rain_codes)
    latest_ten_rain_records = await _get_latest_n_records_by_codes(db, RainfallRecord, rain_codes, limit=10)
    realtime_rainfall_by_code = {
        code: _calculate_realtime_rainfall(latest_ten_rain_records.get(code, []))
        for code in rain_codes
    }
    for code in rain_codes:
        record = latest_rain_records.get(code)
        today_rainfall = None
        if record is None:
            today_rainfall = 0
        elif record.rainfall is not None and record.collection_time >= today:
            today_rainfall = record.rainfall
        today_rainfall_by_code[code] = today_rainfall
        rain_data[code] = {
            "rainfall": today_rainfall,
            "realtime_rainfall": realtime_rainfall_by_code.get(code),
            "raw_counter": record.rainfall if record else None,
            "updated_at": record.collection_time.isoformat() if record else None,
            "status": _resolve_device_health_status(
                probed_status=device_statuses.get(f"rain_{code}", "offline"),
                last_data_time=record.collection_time if record else None,
                stale_after=DEVICE_STATUS_STALE_THRESHOLDS["rain"],
            ),
        }

    runoff_codes = [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]
    runoff_data = {}
    runoff_anomaly_flags = []
    latest_runoff_records = await _get_latest_records_by_codes(db, RunoffRecord, runoff_codes)
    fallback_liquid_pressures = await _get_latest_non_null_fields_by_codes(
        db,
        RunoffRecord,
        [code for code, record in latest_runoff_records.items() if record and record.liquid_pressure is None],
        "liquid_pressure",
    )
    for code in runoff_codes:
        record = latest_runoff_records.get(code)
        if not record:
            continue
        liquid_pressure = record.liquid_pressure
        if liquid_pressure is None:
            liquid_pressure = fallback_liquid_pressures.get(code)
        mapped_rain_code = runoff_rain_mapping.get(code)
        station = {
            "device_code": code,
            "flow_speed": record.flow_speed,
            "flow_rate": record.flow_rate,
            "total_flow": record.total_flow,
            "water_level": record.water_level,
            "sand_content": record.sand_content,
            "liquid_pressure": liquid_pressure,
            "runoff": record.runoff,
            "runoff_unit": "m³/min",
            "rainfall": today_rainfall_by_code.get(mapped_rain_code),
            "rainfall_source_code": mapped_rain_code,
            "updated_at": record.collection_time.isoformat(),
            "status": _resolve_device_health_status(
                probed_status=device_statuses.get(f"runoff_{code}", "offline"),
                last_data_time=record.collection_time,
                stale_after=DEVICE_STATUS_STALE_THRESHOLDS["runoff"],
            ),
        }
        flags = flag_numeric_anomalies(
            station,
            RUNOFF_LATEST_ANOMALY_RULES,
            context={"device_code": code},
        )
        if flags:
            station["has_anomaly"] = True
            station["anomaly_flags"] = flags
            runoff_anomaly_flags.extend(flags)
        runoff_data[code] = station

    insect_image_url = insect.image_url if insect and insect.image_url else await _latest_non_empty_image(db, InsectRecord)
    spore_image_url = None
    if spore and spore.image_url and not await is_probably_black_image(spore.image_url):
        spore_image_url = spore.image_url
    else:
        spore_image_url = await _latest_valid_spore_image(db, spore.image_url if spore else None)

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
            "runoff_anomaly_summary": build_anomaly_summary(runoff_anomaly_flags, subject="总览径流设备"),
            "water_quality": water_quality,
            "rain_gauges": rain_data,
            "device_meta": device_meta,
            "weather_support": weather_support,
        }
    }


def _store_overview_cache(payload: dict, *, now: float | None = None) -> None:
    ttl = max(5, int(settings.OVERVIEW_CACHE_SECONDS))
    base = time.monotonic() if now is None else now
    _overview_cache["value"] = payload
    _overview_cache["expires_at"] = base + ttl


async def _refresh_overview_payload() -> None:
    async with _overview_lock:
        async with AsyncSessionLocal() as session:
            payload = await _build_overview_payload(session)
        _store_overview_cache(payload)


def _clear_overview_refresh_task(task: asyncio.Task) -> None:
    current_task = _overview_cache.get("refresh_task")
    if current_task is task:
        _overview_cache["refresh_task"] = None

    try:
        task.result()
    except Exception as exc:
        logger.warning("Overview background refresh failed: %s", exc)


def _schedule_overview_refresh() -> None:
    current_task = _overview_cache.get("refresh_task")
    if current_task is not None and not current_task.done():
        return

    task = asyncio.create_task(_refresh_overview_payload())
    _overview_cache["refresh_task"] = task
    task.add_done_callback(_clear_overview_refresh_task)


async def _get_cached_overview_payload(db: AsyncSession) -> dict:
    now = time.monotonic()
    cached_value = _overview_cache["value"]
    expires_at = float(_overview_cache["expires_at"])
    if isinstance(cached_value, dict) and now < expires_at:
        return cached_value

    if isinstance(cached_value, dict):
        _schedule_overview_refresh()
        return cached_value

    async with _overview_lock:
        now = time.monotonic()
        cached_value = _overview_cache["value"]
        expires_at = float(_overview_cache["expires_at"])
        if isinstance(cached_value, dict) and now < expires_at:
            return cached_value

        payload = await _build_overview_payload(db)
        _store_overview_cache(payload, now=now)
        return payload


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """大屏首屏所有关键指标一次性返回"""
    return await _get_cached_overview_payload(db)


@router.get("/device-status")
async def get_device_status(db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    """设备在线状态，以设备接口 HTTP 200 为在线依据。"""
    device_statuses = await _get_device_statuses()
    configured_water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    active_water_codes = await resolve_water_quality_codes(db, preferred_code=configured_water_code)
    water_time = None
    if active_water_codes:
        water_latest = await get_latest_water_quality_record(db, active_water_codes)
        water_time = water_latest.collection_time if water_latest else None

    insect_latest_res, spore_latest_res = await asyncio.gather(
        db.execute(select(func.max(InsectRecord.collection_time))),
        db.execute(select(func.max(SporeRecord.collection_time))),
    )
    insect_time = insect_latest_res.scalar_one_or_none()
    spore_time = spore_latest_res.scalar_one_or_none()

    rain_codes = _configured_rain_gauge_codes()
    runoff_codes = _configured_runoff_codes()
    rain_times, runoff_times = await asyncio.gather(
        _get_latest_collection_times_by_codes(db, RainfallRecord, rain_codes),
        _get_latest_collection_times_by_codes(db, RunoffRecord, runoff_codes),
    )

    devices = [
        {
            "name": "智能虫情测报灯",
            "code": settings.INSECT_CODE,
            "status": device_statuses.get("insect", "offline"),
            "last_data": insect_time.isoformat() if insect_time else None,
        },
        {
            "name": "孢子捕捉仪",
            "code": settings.SPORE_CODE,
            "status": device_statuses.get("spore", "offline"),
            "last_data": spore_time.isoformat() if spore_time else None,
        },
        {
            "name": "面源污染监测站",
            "code": configured_water_code,
            "status": _resolve_device_health_status(
                probed_status=device_statuses.get("water", "offline"),
                last_data_time=water_time,
                stale_after=DEVICE_STATUS_STALE_THRESHOLDS["water"],
                now=now,
            ),
            "last_data": water_time.isoformat() if water_time else None,
        },
    ]

    for index, code in enumerate(rain_codes, 1):
        record_time = rain_times.get(code)
        devices.append({
            "name": f"4G雨量计{index}号",
            "code": code,
            "status": _resolve_device_health_status(
                probed_status=device_statuses.get(f"rain_{code}", "offline"),
                last_data_time=record_time,
                stale_after=DEVICE_STATUS_STALE_THRESHOLDS["rain"],
                now=now,
            ),
            "last_data": record_time.isoformat() if record_time else None,
        })

    runoff_names = {code: name for code, name in RUNOFF_DEVICES}
    for code in runoff_codes:
        record_time = runoff_times.get(code)
        devices.append({
            "name": runoff_names.get(code, code),
            "code": code,
            "status": _resolve_device_health_status(
                probed_status=device_statuses.get(f"runoff_{code}", "offline"),
                last_data_time=record_time,
                stale_after=DEVICE_STATUS_STALE_THRESHOLDS["runoff"],
                now=now,
            ),
            "last_data": record_time.isoformat() if record_time else None,
        })

    return {"data": devices}
