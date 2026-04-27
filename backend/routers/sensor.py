from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import RainfallRecord, RunoffRecord, WaterLevelRecord


router = APIRouter(prefix="/api/sensor", tags=["传感器"])


@router.get("/rainfall/latest")
async def get_latest_rainfall(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RainfallRecord).order_by(desc(RainfallRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "rainfall": record.rainfall,
            "daily_rainfall": record.daily_rainfall,
        }
    }


@router.get("/runoff/latest")
async def get_latest_runoff(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunoffRecord).order_by(desc(RunoffRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "flow_rate": record.flow_rate,
            "total_flow": record.total_flow,
        }
    }


@router.get("/waterlevel/latest")
async def get_latest_waterlevel(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WaterLevelRecord).order_by(desc(WaterLevelRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "water_level": record.water_level,
        }
    }


@router.get("/water_quality/daily")
async def get_wq_daily(
    days: int = Query(30, ge=7, le=90), db: AsyncSession = Depends(get_db)
):
    since = datetime.now() - timedelta(days=days - 1)
    from models import WaterQualityRecord

    water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    result = await db.execute(
        select(WaterQualityRecord)
        .where(
            WaterQualityRecord.device_code == water_code,
            WaterQualityRecord.collection_time
            >= since.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        .order_by(WaterQualityRecord.collection_time)
    )
    records = result.scalars().all()

    daily = defaultdict(lambda: {"permanganate": [], "tn": [], "tp": [], "nh4n": []})
    for record in records:
        day = record.collection_time.date().isoformat()
        bucket = daily[day]
        if record.permanganate_index is not None:
            bucket["permanganate"].append(record.permanganate_index)
        if record.total_nitrogen is not None:
            bucket["tn"].append(record.total_nitrogen)
        if record.total_phosphorus is not None:
            bucket["tp"].append(record.total_phosphorus)
        if record.ammonia_nitrogen is not None:
            bucket["nh4n"].append(record.ammonia_nitrogen)

    res = []
    curr = since.date()
    today = datetime.now().date()
    while curr <= today:
        day = curr.isoformat()
        values = daily.get(day, {})
        res.append(
            {
                "date": day,
                "permanganate": (
                    round(sum(values["permanganate"]) / len(values["permanganate"]), 2)
                    if values.get("permanganate")
                    else None
                ),
                "tn": (
                    round(sum(values["tn"]) / len(values["tn"]), 2)
                    if values.get("tn")
                    else None
                ),
                "tp": (
                    round(sum(values["tp"]) / len(values["tp"]), 3)
                    if values.get("tp")
                    else None
                ),
                "nh4n": (
                    round(sum(values["nh4n"]) / len(values["nh4n"]), 2)
                    if values.get("nh4n")
                    else None
                ),
            }
        )
        curr += timedelta(days=1)
    return {"data": res}


@router.get("/runoff/daily")
async def get_runoff_daily(
    days: int = Query(30, ge=7, le=90), db: AsyncSession = Depends(get_db)
):
    since = datetime.now() - timedelta(days=days - 1)
    from models import RunoffRecord

    result = await db.execute(
        select(RunoffRecord)
        .where(
            RunoffRecord.collection_time
            >= since.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        .order_by(RunoffRecord.collection_time)
    )
    records = result.scalars().all()

    daily = defaultdict(
        lambda: {
            "sand": [],
            "flow": [],
            "speed": [],
            "total": [],
            "level": [],
            "rain": 0,
            "runoff": 0,
            "press": [],
        }
    )
    for record in records:
        day = record.collection_time.date().isoformat()
        if record.sand_content is not None:
            daily[day]["sand"].append(record.sand_content)
        if record.flow_rate is not None:
            daily[day]["flow"].append(record.flow_rate)
        if record.flow_speed is not None:
            daily[day]["speed"].append(record.flow_speed)
        if record.total_flow is not None:
            daily[day]["total"].append(record.total_flow)
        if record.water_level is not None:
            daily[day]["level"].append(record.water_level)
        if record.liquid_pressure is not None:
            daily[day]["press"].append(record.liquid_pressure)
        daily[day]["rain"] += record.rainfall or 0
        daily[day]["runoff"] += record.runoff or 0

    res = []
    curr = since.date()
    today = datetime.now().date()
    while curr <= today:
        day = curr.isoformat()
        values = daily.get(day, {})
        res.append(
            {
                "date": day,
                "sand": (
                    round(sum(values["sand"]) / len(values["sand"]), 2)
                    if values.get("sand")
                    else None
                ),
                "flow": (
                    round(sum(values["flow"]) / len(values["flow"]), 2)
                    if values.get("flow")
                    else None
                ),
                "flow_speed": (
                    round(sum(values["speed"]) / len(values["speed"]), 2)
                    if values.get("speed")
                    else None
                ),
                "total_flow": (
                    round(max(values["total"]), 1) if values.get("total") else None
                ),
                "water_level": (
                    round(sum(values["level"]) / len(values["level"]), 2)
                    if values.get("level")
                    else None
                ),
                "rainfall": round(values.get("rain", 0), 1),
                "runoff": round(values.get("runoff", 0), 1),
                "liquid_pressure": (
                    round(sum(values["press"]) / len(values["press"]), 1)
                    if values.get("press")
                    else None
                ),
            }
        )
        curr += timedelta(days=1)
    return {"data": res}
