"""地表径流监测系统数据采集 (WHXPH data-n latest record API)."""
import logging
import re
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import RunoffRecord, CollectLog, RainfallRecord
from config import settings
import httpx

logger = logging.getLogger(__name__)

# 设备配置：测试ID -> 名称
RUNOFF_DEVICES = {
    "16132920": "杧果林径流1",
    "16132921": "橡胶林径流1",
    "16132922": "次生林径流",
    "16132923": "杧果林径流2",
    "16132924": "橡胶林径流2",
    "16132925": "槟榔林径流",
}

# 字段映射：API返回中文名 -> RunoffRecord字段
RUNOFF_FIELD_MAP = {
    "瞬时流量": "flow_rate",
    "流量":     "flow_rate",
    "流速":     "flow_speed",
    "累计流量": "total_flow",
    "液位":     "water_level",
    "水位":     "water_level",
    "雨量":     "rainfall",
    "降雨量":   "rainfall",
    "雨量累计": "rainfall",
    "含沙量":   "sand_content",
    "液位压力": "liquid_pressure",
    "径流":     "runoff",
}

SORTED_RUNOFF_KEYWORDS = sorted(RUNOFF_FIELD_MAP.items(), key=lambda item: len(item[0]), reverse=True)


def _parse_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


async def _fetch_whxph_latest(device_id: str) -> dict:
    url = f"{settings.WHXPH_BASE_URL.rstrip('/')}/data-n/{device_id}"
    async with httpx.AsyncClient(verify=False, timeout=20) as client:
        resp = await client.get(url, headers={"accept": "*/*"})
        resp.raise_for_status()
        data = resp.json()
    return data if isinstance(data, dict) and data.get("deviceId") else {}


def _extract_fields(ele_lists: list[dict]) -> dict:
    """从 eleLists 提取 RunoffRecord 字段."""
    result = {}
    for item in ele_lists:
        cn_name = (item.get("eName", "") or "").strip()
        normalized_name = re.sub(r"[（(].*?[）)]", "", cn_name).strip()
        field_name = RUNOFF_FIELD_MAP.get(cn_name) or RUNOFF_FIELD_MAP.get(normalized_name)
        if not field_name:
            for keyword, mapped_field in SORTED_RUNOFF_KEYWORDS:
                if keyword in cn_name or keyword in normalized_name:
                    field_name = mapped_field
                    break
        if field_name and field_name not in result:
            result[field_name] = _parse_float(item.get("eValue"))
    return result


async def _has_collection_time(
    db: AsyncSession,
    model,
    device_code: str,
    collection_time: datetime,
) -> bool:
    result = await db.execute(
        select(model.id)
        .where(
            model.device_code == device_code,
            model.collection_time == collection_time,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def collect_runoff(db: AsyncSession) -> int:
    """采集 6 台地表径流设备最新一条数据 (WHXPH data-n)."""
    codes = [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]
    if not codes:
        return 0

    total_saved = 0

    for code in codes:
        name = RUNOFF_DEVICES.get(code, code)
        try:
            data = await _fetch_whxph_latest(code)
        except Exception as e:
            logger.error(f"collect_runoff [{name}] request error: {e}")
            db.add(CollectLog(task_name=f"runoff_{code}", status="error", message=str(e)))
            await db.commit()
            continue

        ele_lists = data.get("eleLists") or []
        if not ele_lists:
            db.add(CollectLog(task_name=f"runoff_{code}", status="success", records_count=0))
            await db.commit()
            continue

        saved = 0
        try:
            col_time_str = data.get("datetime", "")
            col_time = (
                datetime.strptime(col_time_str, "%Y-%m-%d %H:%M:%S")
                if col_time_str else datetime.now()
            )
            if not await _has_collection_time(db, RunoffRecord, code, col_time):
                fields = _extract_fields(ele_lists)
                db.add(RunoffRecord(
                    device_code=code,
                    collection_time=col_time,
                    raw_data=data,
                    **fields,
                ))
                saved = 1
        except Exception as e:
            logger.warning(f"collect_runoff [{name}] parse error: {e}")

        db.add(CollectLog(task_name=f"runoff_{code}", status="success", records_count=saved))
        await db.commit()
        total_saved += saved
        logger.info(f"collect_runoff [{code} {name}]: saved {saved} records")

    return total_saved


async def collect_rain_gauges(db: AsyncSession) -> int:
    """采集 4G 雨量计最新一条数据 (WHXPH data-n)."""
    codes = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    if not codes:
        return 0

    total_saved = 0

    for code in codes:
        try:
            data = await _fetch_whxph_latest(code)
        except Exception as e:
            logger.error(f"collect_rain_gauges [{code}] error: {e}")
            continue

        ele_lists = data.get("eleLists") or []
        if not ele_lists:
            continue

        try:
            col_time_str = data.get("datetime", "")
            col_time = (
                datetime.strptime(col_time_str, "%Y-%m-%d %H:%M:%S")
                if col_time_str else datetime.now()
            )
            if not await _has_collection_time(db, RainfallRecord, code, col_time):
                rainfall = _extract_fields(ele_lists).get("rainfall")
                db.add(RainfallRecord(
                    device_code=code,
                    collection_time=col_time,
                    rainfall=rainfall,
                    raw_data=data,
                ))
                total_saved += 1
        except Exception as e:
            logger.warning(f"collect_rain_gauges [{code}] parse error: {e}")

        await db.commit()
        logger.info(f"collect_rain_gauges [{code}]: saved records")

    return total_saved
