"""农田排水水质监测系统数据采集 (WHXPH platform)."""
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from models import WaterQualityRecord, CollectLog
from config import settings
from collectors.runoff import _fetch_whxph_latest, _parse_float

logger = logging.getLogger(__name__)

# 字段映射：API返回中文名 -> WaterQualityRecord字段
WQ_FIELD_MAP = {
    "PH": "ph",
    "pH": "ph",
    "溶解氧": "dissolved_oxygen",
    "电导率": "conductivity",
    "浊度": "turbidity",
    "氨氮": "ammonia_nitrogen",
    "总磷": "total_phosphorus",
    "总氮": "total_nitrogen",
    "COD": "cod",
    "水温": "temperature",
}

async def collect_water_quality(db: AsyncSession) -> int:
    """采集 1 台农田排水水质监测设备最新一条数据."""
    code = settings.WATER_QUALITY_CODE.strip()
    if not code:
        logger.warning("WATER_QUALITY_CODE is not set, skipping.")
        return 0

    try:
        data = await _fetch_whxph_latest(code)
    except Exception as e:
        logger.error(f"collect_water_quality [{code}] request error: {e}")
        db.add(CollectLog(task_name=f"wq_{code}", status="error", message=str(e)))
        await db.commit()
        return 0

    ele_lists = data.get("eleLists") or []
    if not ele_lists:
        db.add(CollectLog(task_name=f"wq_{code}", status="success", records_count=0))
        await db.commit()
        return 0

    try:
        col_time_str = data.get("datetime", "")
        col_time = (
            datetime.strptime(col_time_str, "%Y-%m-%d %H:%M:%S")
            if col_time_str else datetime.now()
        )
        
        # 提取字段
        fields = {}
        for item in ele_lists:
            cn_name = item.get("eName", "")
            field_name = WQ_FIELD_MAP.get(cn_name)
            if field_name and field_name not in fields:
                fields[field_name] = _parse_float(item.get("eValue"))

        record = WaterQualityRecord(
            device_code=code,
            collection_time=col_time,
            raw_data=data,
            **fields
        )
        db.add(record)
        db.add(CollectLog(task_name=f"wq_{code}", status="success", records_count=1))
        await db.commit()
        logger.info(f"collect_water_quality [{code}]: saved 1 record")
        return 1
    except Exception as e:
        logger.warning(f"collect_water_quality [{code}] parse error: {e}")
        await db.rollback()
        return 0
