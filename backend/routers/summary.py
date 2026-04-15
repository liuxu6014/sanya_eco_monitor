"""综合概览接口 — 大屏首屏所需数据的一次性汇总."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from database import get_db
from models import (
    InsectRecord, SporeRecord, WeatherRecord, SoilRecord, 
    RainfallRecord, RunoffRecord, CollectLog, WaterQualityRecord
)
from config import settings

router = APIRouter(prefix="/api/summary", tags=["综合概览"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """大屏首屏所有关键指标一次性返回"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 分级在线判定阈值
    REALTIME_THRESHOLD = datetime.now() - timedelta(minutes=15)
    PERIODIC_THRESHOLD = datetime.now() - timedelta(hours=48)

    def get_status(t, is_realtime=True):
        if t is None: return "offline"
        limit = REALTIME_THRESHOLD if is_realtime else PERIODIC_THRESHOLD
        return "online" if t >= limit else "timeout"

    # Latest weather
    weather_res = await db.execute(
        select(WeatherRecord).order_by(desc(WeatherRecord.collection_time)).limit(1)
    )
    weather = weather_res.scalar_one_or_none()

    # Latest soil
    soil_res = await db.execute(
        select(SoilRecord).order_by(desc(SoilRecord.collection_time)).limit(1)
    )
    soil = soil_res.scalar_one_or_none()

    # Latest insect
    insect_res = await db.execute(
        select(InsectRecord).order_by(desc(InsectRecord.collection_time)).limit(1)
    )
    insect = insect_res.scalar_one_or_none()

    # Latest spore
    spore_res = await db.execute(
        select(SporeRecord).order_by(desc(SporeRecord.collection_time)).limit(1)
    )
    spore = spore_res.scalar_one_or_none()

    # Today's insect total
    today_insect_res = await db.execute(
        select(func.sum(InsectRecord.total_count)).where(InsectRecord.collection_time >= today)
    )
    today_insect_total = today_insect_res.scalar() or 0

    # 7-day insect trend
    week_ago = datetime.now() - timedelta(days=7)
    trend_res = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= week_ago)
        .order_by(InsectRecord.collection_time)
    )
    trend_records = trend_res.scalars().all()
    daily_trend: dict = {}
    for r in trend_records:
        day = r.collection_time.strftime("%m-%d")
        daily_trend[day] = daily_trend.get(day, 0) + r.total_count

    # Last collect log
    log_res = await db.execute(
        select(CollectLog).order_by(desc(CollectLog.created_at)).limit(5)
    )
    logs = log_res.scalars().all()

    # --- ADDED: Actual data for other individual devices on the map ---
    async def get_latest_by_code(model, code):
        res = await db.execute(
            select(model).where(model.device_code == code).order_by(desc(model.collection_time)).limit(1)
        )
        return res.scalar_one_or_none()

    # 1. Runoff devices
    runoff_data = {}
    RUNOFF_CODES = [c.strip() for c in settings.RUNOFF_CODES.split(",") if c.strip()]
    for code in RUNOFF_CODES:
        r = await get_latest_by_code(RunoffRecord, code)
        if r:
            runoff_data[code] = {
                "device_code": code,
                "flow_speed": r.flow_speed,
                "flow_rate": r.flow_rate,
                "total_flow": r.total_flow,
                "water_level": r.water_level,
                "sand_content": r.sand_content,
                "liquid_pressure": r.liquid_pressure,
                "runoff": r.runoff,
                "rainfall": r.rainfall,
                "updated_at": r.collection_time.isoformat(),
                "status": get_status(r.collection_time, is_realtime=True)
            }

    # 2. Water quality
    wq_code = settings.WATER_QUALITY_CODE.strip() or "16116030"
    wq = await get_latest_by_code(WaterQualityRecord, wq_code)
    wq_data = {
        "ph": wq.ph,
        "ec": wq.conductivity,
        "cod": wq.cod,
        "nh4n": wq.ammonia_nitrogen,
        "do": wq.dissolved_oxygen,
        "tp": wq.total_phosphorus,
        "tn": wq.total_nitrogen,
        "turbidity": wq.turbidity,
        "water_temp": wq.temperature,
        "updated_at": wq.collection_time.isoformat(),
        "status": get_status(wq.collection_time, is_realtime=True)
    } if wq else None

    # 3. Rain gauges
    rain_data = {}
    RAIN_CODES = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    for code in RAIN_CODES:
        r = await get_latest_by_code(RainfallRecord, code)
        if r:
            rain_data[code] = {
                "rainfall": r.rainfall,
                "updated_at": r.collection_time.isoformat(),
                "status": get_status(r.collection_time, is_realtime=True)
            }

    return {
        "data": {
            "weather": {
                "temperature": weather.temperature if weather else None,
                "humidity": weather.humidity if weather else None,
                "wind_speed": weather.wind_speed if weather else None,
                "wind_direction": weather.wind_direction if weather else None,
                "rainfall": weather.rainfall if weather else None,
                "updated_at": weather.collection_time.isoformat() if weather else None,
            },
            "soil": {
                "moisture_10cm": soil.moisture_10cm if soil else None,
                "moisture_20cm": soil.moisture_20cm if soil else None,
                "moisture_40cm": soil.moisture_40cm if soil else None,
                "temperature_10cm": soil.temperature_10cm if soil else None,
                "n": soil.nitrogen if soil else None,
                "p": soil.phosphorus if soil else None,
                "k": soil.potassium if soil else None,
                "ph": soil.ph if soil else None,
                "ec": soil.conductivity if soil else None,
                "updated_at": soil.collection_time.isoformat() if soil else None,
            },
            "insect": {
                "total_today": int(today_insect_total),
                "latest_count": insect.total_count if insect else None,
                "top_species": sorted(
                    (insect.species_data or {}).items(), key=lambda x: x[1], reverse=True
                )[:5] if insect else [],
                "image_url": insect.image_url if insect else None,
                "updated_at": insect.collection_time.isoformat() if insect else None,
                "status": get_status(insect.collection_time, is_realtime=False) if insect else "offline",
            },
            "spore": {
                "latest_count": spore.total_count if spore else None,
                "image_url": spore.image_url if spore else None,
                "updated_at": spore.collection_time.isoformat() if spore else None,
                "status": get_status(spore.collection_time, is_realtime=False) if spore else "offline",
            },
            "insect_trend": [
                {"date": k, "count": v} for k, v in daily_trend.items()
            ],
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
            "water_quality": wq_data,
            "rain_gauges": rain_data,
        }
    }


@router.get("/device-status")
async def get_device_status(db: AsyncSession = Depends(get_db)):
    """设备在线状态（以最近数据时间判断是否在线）"""
    # 分级在线判定阈值
    REALTIME_LIMIT = datetime.now() - timedelta(minutes=15)
    PERIODIC_LIMIT = datetime.now() - timedelta(hours=48)

    async def last_time(model, code=None):
        q = select(model.collection_time).order_by(desc(model.collection_time)).limit(1)
        if code is not None:
            q = q.where(model.device_code == code)
        res = await db.execute(q)
        return res.scalar_one_or_none()

    insect_t  = await last_time(InsectRecord)
    spore_t   = await last_time(SporeRecord)
    wq_code   = settings.WATER_QUALITY_CODE.strip() or "16116030"
    wq_t      = await last_time(WaterQualityRecord, wq_code)

    def status(t, is_realtime=True):
        if t is None:
            return "offline"
        limit = REALTIME_LIMIT if is_realtime else PERIODIC_LIMIT
        return "online" if t >= limit else "timeout"

    devices = [
        {"name": "智能虫情测报灯", "code": "insect", "status": status(insect_t, is_realtime=False), "last_data": insect_t.isoformat() if insect_t else None},
        {"name": "孢子捕捉仪",     "code": "spore",  "status": status(spore_t, is_realtime=False), "last_data": spore_t.isoformat()  if spore_t  else None},
        {"name": "面源污染监测站", "code": "water",  "status": status(wq_t, is_realtime=True),     "last_data": wq_t.isoformat() if wq_t else None},
    ]

    RAIN_CODES = [c.strip() for c in settings.RAIN_GAUGE_CODES.split(",") if c.strip()]
    for i, code in enumerate(RAIN_CODES, 1):
        t = await last_time(RainfallRecord, code)
        devices.append({"name": f"4G雨量计{i}号", "code": f"rain_{code}", "status": status(t, True), "last_data": t.isoformat() if t else None})

    RUNOFF_DEVICES = [
        ("16132920", "杧果林径流监测系统1号"),
        ("16132921", "橡胶林径流监测系统1号"),
        ("16132922", "次生林径流监测系统"),
        ("16132923", "杧果林径流监测系统2号"),
        ("16132924", "橡胶林径流监测系统2号"),
        ("16132925", "槟榔林径流监测系统"),
    ]
    for code, name in RUNOFF_DEVICES:
        t = await last_time(RunoffRecord, code)
        devices.append({"name": name, "code": f"runoff_{code}", "status": status(t, True), "last_data": t.isoformat() if t else None})

    return {"data": devices}
