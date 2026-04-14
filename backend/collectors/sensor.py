"""气象 & 墒情传感器数据采集."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from collectors.base import get_token
from models import WeatherRecord, SoilRecord, CollectLog
from config import settings
import httpx

logger = logging.getLogger(__name__)


async def sensor_get(path: str, params: dict | None = None) -> dict:
    """Authenticated GET using SENSOR_BASE_URL."""
    token = await get_token()
    async with httpx.AsyncClient(verify=False, timeout=20) as client:
        resp = await client.get(
            f"{settings.SENSOR_BASE_URL}{path}",
            params=params,
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return resp.json()


# 实际API返回格式: data.list[i] = {"大气温度": "5.1", "风速": "0.0", "collectionTime": "...", ...}
WEATHER_FIELD_MAP = {
    "大气温度": "temperature",
    "空气温度": "temperature",
    "大气湿度": "humidity",
    "空气湿度": "humidity",
    "风速": "wind_speed",
    "风向": "wind_direction",
    "雨量": "rainfall",
    "雨量累计": "rainfall",
    "降雨量": "rainfall",
    "数字气压": "pressure",
    "模拟气压": "pressure",
    "照度": "light",
    "光照": "light",
}

SOIL_FIELD_MAP = {
    "土壤湿度": "moisture_10cm",
    "土壤湿度1": "moisture_10cm",
    "土壤湿度2": "moisture_20cm",
    "土壤湿度3": "moisture_40cm",
    "土壤温度": "temperature_10cm",
    "土壤温度1": "temperature_10cm",
    "土壤温度2": "temperature_20cm",
    "土壤温度3": "temperature_40cm",
    "pH值": "ph",
    "电导率": "conductivity",
    "氮离子": "nitrogen",
    "磷离子": "phosphorus",
    "钾离子": "potassium",
}


def _build_time_range(hours_back: int = 2) -> str:
    end = datetime.now()
    start = end - timedelta(hours=hours_back)
    fmt = "%Y-%m-%d %H:%M:%S"
    return f"{start.strftime(fmt)},{end.strftime(fmt)}"


def _parse_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _extract_fields_from_flat(item: dict, field_map: dict) -> dict:
    """从扁平字典 {"大气温度": "5.1", ...} 提取字段."""
    result = {}
    for cn_name, field_name in field_map.items():
        if cn_name in item and field_name not in result:
            result[field_name] = _parse_float(item[cn_name])
    return result


async def _save_record(db: AsyncSession, item: dict, device_code: str):
    """Parses a single record and saves to Weather and/or Soil tables."""
    col_time_str = item.get("collectionTime", "")
    try:
        col_time = datetime.strptime(col_time_str[:16], "%Y-%m-%d %H:%M") if col_time_str else datetime.now()
    except Exception:
        col_time = datetime.now()

    # 1. Weather Data
    w_fields = _extract_fields_from_flat(item, WEATHER_FIELD_MAP)
    if w_fields:
        db.add(WeatherRecord(
            device_code=device_code,
            collection_time=col_time,
            raw_data=item,
            **w_fields
        ))

    # 2. Soil Data
    s_fields = _extract_fields_from_flat(item, SOIL_FIELD_MAP)
    if s_fields:
        db.add(SoilRecord(
            device_code=device_code,
            collection_time=col_time,
            raw_data=item,
            **s_fields
        ))


async def collect_weather(db: AsyncSession) -> int:
    time_range = _build_time_range()
    try:
        data = await sensor_get(
            "/http/monitor/getSensorByCode",
            params={"code": settings.WEATHER_CODE, "collectionTime": time_range},
        )
    except Exception as e:
        logger.error(f"collect_weather error: {e}")
        db.add(CollectLog(task_name="weather", status="error", message=str(e)))
        await db.commit()
        return 0

    inner = data.get("data") or {}
    records_data = inner.get("list") or []

    for item in records_data:
        await _save_record(db, item, settings.WEATHER_CODE)

    db.add(CollectLog(task_name="weather", status="success", records_count=len(records_data)))
    await db.commit()
    logger.info(f"collect_weather: processed {len(records_data)} records")
    return len(records_data)


async def collect_soil(db: AsyncSession) -> int:
    time_range = _build_time_range()
    try:
        data = await sensor_get(
            "/http/monitor/getSensorByCode",
            params={"code": settings.SOIL_CODE, "collectionTime": time_range},
        )
    except Exception as e:
        logger.error(f"collect_soil error: {e}")
        db.add(CollectLog(task_name="soil", status="error", message=str(e)))
        await db.commit()
        return 0

    inner = data.get("data") or {}
    records_data = inner.get("list") or []

    for item in records_data:
        await _save_record(db, item, settings.SOIL_CODE)

    db.add(CollectLog(task_name="soil", status="success", records_count=len(records_data)))
    await db.commit()
    logger.info(f"collect_soil: processed {len(records_data)} records")
    return len(records_data)
