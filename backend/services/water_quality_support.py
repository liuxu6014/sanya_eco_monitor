from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import WaterQualityRecord


async def get_water_quality_code_stats(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            WaterQualityRecord.device_code,
            func.count(WaterQualityRecord.id).label("record_count"),
            func.max(WaterQualityRecord.collection_time).label("latest_time"),
        )
        .group_by(WaterQualityRecord.device_code)
        .order_by(func.count(WaterQualityRecord.id).desc(), func.max(WaterQualityRecord.collection_time).desc())
    )
    return [
        {
            "device_code": row[0],
            "record_count": row[1],
            "latest_time": row[2],
        }
        for row in result.all()
    ]


async def get_water_quality_codes(db: AsyncSession) -> list[str]:
    return [item["device_code"] for item in await get_water_quality_code_stats(db)]


async def resolve_water_quality_codes(
    db: AsyncSession,
    *,
    preferred_code: str | None = None,
    start_dt=None,
    end_dt=None,
) -> list[str]:
    period_query = select(
        WaterQualityRecord.device_code,
        func.count(WaterQualityRecord.id).label("record_count"),
        func.max(WaterQualityRecord.collection_time).label("latest_time"),
    ).group_by(WaterQualityRecord.device_code)
    if start_dt is not None:
        period_query = period_query.where(WaterQualityRecord.collection_time >= start_dt)
    if end_dt is not None:
        period_query = period_query.where(WaterQualityRecord.collection_time <= end_dt)
    period_query = period_query.order_by(
        func.count(WaterQualityRecord.id).desc(),
        func.max(WaterQualityRecord.collection_time).desc(),
    )
    result = await db.execute(period_query)
    period_stats = result.all()
    if not period_stats:
        return []

    top_code = period_stats[0][0]
    top_count = int(period_stats[0][1] or 0)
    if preferred_code:
        for row in period_stats:
            code = row[0]
            count = int(row[1] or 0)
            if code == preferred_code and count >= top_count:
                return [preferred_code]

    if top_code:
        return [top_code]

    stats = await get_water_quality_code_stats(db)
    if preferred_code and any(item["device_code"] == preferred_code for item in stats):
        return [preferred_code]

    return [stats[0]["device_code"]] if stats else []


async def get_latest_water_quality_record(
    db: AsyncSession,
    codes: list[str] | None = None,
):
    query = select(WaterQualityRecord)
    if codes:
        query = query.where(WaterQualityRecord.device_code.in_(codes))
    query = query.order_by(desc(WaterQualityRecord.collection_time)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_water_quality_records(
    db: AsyncSession,
    *,
    start_dt=None,
    end_dt=None,
    codes: list[str] | None = None,
):
    query = select(WaterQualityRecord)
    if codes:
        query = query.where(WaterQualityRecord.device_code.in_(codes))
    if start_dt is not None:
        query = query.where(WaterQualityRecord.collection_time >= start_dt)
    if end_dt is not None:
        query = query.where(WaterQualityRecord.collection_time <= end_dt)
    query = query.order_by(WaterQualityRecord.collection_time)
    result = await db.execute(query)
    return result.scalars().all()
