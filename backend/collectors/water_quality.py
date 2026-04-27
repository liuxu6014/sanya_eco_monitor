"""Water-quality collection from the WHXPH platform."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.runoff import _fetch_whxph_latest, _parse_float
from config import settings
from models import CollectLog, WaterQualityRecord


logger = logging.getLogger(__name__)


WQ_FIELD_MAP = {
    "氨氮": "ammonia_nitrogen",
    "总磷": "total_phosphorus",
    "总氮": "total_nitrogen",
    "高猛酸盐": "permanganate_index",
    "高锰酸盐": "permanganate_index",
    "高锰酸盐指数": "permanganate_index",
}


async def _has_collection_time(
    db: AsyncSession,
    device_code: str,
    collection_time: datetime,
) -> bool:
    result = await db.execute(
        select(WaterQualityRecord.id)
        .where(
            WaterQualityRecord.device_code == device_code,
            WaterQualityRecord.collection_time == collection_time,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def collect_water_quality(db: AsyncSession) -> int:
    """Collect the latest record from the configured water-quality device."""
    code = settings.WATER_QUALITY_CODE.strip()
    if not code:
        logger.warning("WATER_QUALITY_CODE is not set, skipping.")
        return 0

    try:
        data = await _fetch_whxph_latest(code)
    except Exception as exc:
        logger.error("collect_water_quality [%s] request error: %s", code, exc)
        db.add(CollectLog(task_name=f"wq_{code}", status="error", message=str(exc)))
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
            if col_time_str
            else datetime.now()
        )

        if await _has_collection_time(db, code, col_time):
            db.add(CollectLog(task_name=f"wq_{code}", status="success", records_count=0))
            await db.commit()
            logger.info("collect_water_quality [%s]: duplicate skipped", code)
            return 0

        fields: dict[str, float | None] = {}
        for item in ele_lists:
            field_name = WQ_FIELD_MAP.get(item.get("eName", ""))
            if field_name and field_name not in fields:
                fields[field_name] = _parse_float(item.get("eValue"))

        record = WaterQualityRecord(
            device_code=code,
            collection_time=col_time,
            raw_data=data,
            **fields,
        )
        db.add(record)
        db.add(CollectLog(task_name=f"wq_{code}", status="success", records_count=1))
        await db.commit()
        logger.info("collect_water_quality [%s]: saved 1 record", code)
        return 1
    except Exception as exc:
        logger.warning("collect_water_quality [%s] parse error: %s", code, exc)
        await db.rollback()
        return 0
