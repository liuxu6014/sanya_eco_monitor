import logging
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from models import RainfallRecord, RunoffRecord, WaterLevelRecord, CollectLog
from config import settings

logger = logging.getLogger(__name__)

async def whxph_get(device_id: str) -> dict:
    if not device_id:
        return {}

    url = f"{settings.WHXPH_BASE_URL.rstrip('/')}/data-n/{device_id}"
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            resp = await client.get(url, headers={"accept": "*/*"})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("deviceId"):
                return data
            else:
                logger.warning(f"WHXPH API get failed for {device_id}: {data}")
                return {}
    except Exception as e:
        logger.error(f"WHXPH API request error for {device_id}: {e}")
        return {}


def _extract_whxph_value(ele_lists: list, keywords: list[str]) -> float | None:
    for e in ele_lists:
        name = e.get("eName", "")
        if any(k in name for k in keywords):
            try:
                return float(e.get("eValue"))
            except (ValueError, TypeError):
                return None
    return None


async def collect_rain_gauge(db: AsyncSession) -> int:
    """采集 雨量计 数据"""
    device_id = settings.RAIN_GAUGE_ID
    if not device_id:
        return 0

    data = await whxph_get(device_id)
    ele_lists = data.get("eleLists") or []
    if not ele_lists:
        return 0

    rainfall = _extract_whxph_value(ele_lists, ["雨量", "降雨量"])

    time_str = data.get("datetime", "")
    col_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") if time_str else datetime.now()

    record = RainfallRecord(
        device_code=device_id,
        collection_time=col_time,
        rainfall=rainfall,
        raw_data=data
    )
    db.add(record)
    db.add(CollectLog(task_name="rain_gauge", status="success", records_count=1))
    await db.commit()
    logger.info("collect_rain_gauge: saved 1 record")
    return 1


async def collect_flow_meter(db: AsyncSession) -> int:
    """采集 流量计 数据"""
    device_id = settings.FLOW_METER_ID
    if not device_id:
        return 0

    data = await whxph_get(device_id)
    ele_lists = data.get("eleLists") or []
    if not ele_lists:
        return 0

    flow_rate = _extract_whxph_value(ele_lists, ["瞬时流量", "流速", "流量", "径流"])
    total_flow = _extract_whxph_value(ele_lists, ["累计流量"])

    time_str = data.get("datetime", "")
    col_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") if time_str else datetime.now()

    record = RunoffRecord(
        device_code=device_id,
        collection_time=col_time,
        flow_rate=flow_rate,
        total_flow=total_flow,
        raw_data=data
    )
    db.add(record)
    db.add(CollectLog(task_name="flow_meter", status="success", records_count=1))
    await db.commit()
    logger.info("collect_flow_meter: saved 1 record")
    return 1


async def collect_level_gauge(db: AsyncSession) -> int:
    """采集 液位计 数据"""
    device_id = settings.LEVEL_GAUGE_ID
    if not device_id:
        return 0

    data = await whxph_get(device_id)
    ele_lists = data.get("eleLists") or []
    if not ele_lists:
        return 0

    water_level = _extract_whxph_value(ele_lists, ["液位", "水位"])

    time_str = data.get("datetime", "")
    col_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") if time_str else datetime.now()

    record = WaterLevelRecord(
        device_code=device_id,
        collection_time=col_time,
        water_level=water_level,
        raw_data=data
    )
    db.add(record)
    db.add(CollectLog(task_name="level_gauge", status="success", records_count=1))
    await db.commit()
    logger.info("collect_level_gauge: saved 1 record")
    return 1
