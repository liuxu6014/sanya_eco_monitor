from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models import WeatherRecord, SoilRecord, RainfallRecord, RunoffRecord, WaterLevelRecord

router = APIRouter(prefix="/api/sensor", tags=["传感器"])


@router.get("/weather/latest")
async def get_latest_weather(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WeatherRecord).order_by(desc(WeatherRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "temperature": record.temperature,
            "humidity": record.humidity,
            "wind_speed": record.wind_speed,
            "wind_direction": record.wind_direction,
            "rainfall": record.rainfall,
            "pressure": record.pressure,
            "light": record.light,
        }
    }


@router.get("/weather/trend")
async def get_weather_trend(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """近N小时气象趋势（逐条记录）"""
    since = datetime.now() - timedelta(hours=hours)
    result = await db.execute(
        select(WeatherRecord)
        .where(WeatherRecord.collection_time >= since)
        .order_by(WeatherRecord.collection_time)
    )
    records = result.scalars().all()
    return {
        "data": [
            {
                "time": r.collection_time.isoformat(),
                "temperature": r.temperature,
                "humidity": r.humidity,
                "wind_speed": r.wind_speed,
                "rainfall": r.rainfall,
            }
            for r in records
        ]
    }


@router.get("/soil/latest")
async def get_latest_soil(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SoilRecord).order_by(desc(SoilRecord.collection_time)).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "moisture_10cm": record.moisture_10cm,
            "moisture_20cm": record.moisture_20cm,
            "moisture_40cm": record.moisture_40cm,
            "temperature_10cm": record.temperature_10cm,
        }
    }


@router.get("/soil/trend")
async def get_soil_trend(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now() - timedelta(hours=hours)
    result = await db.execute(
        select(SoilRecord)
        .where(SoilRecord.collection_time >= since)
        .order_by(SoilRecord.collection_time)
    )
    records = result.scalars().all()
    return {
        "data": [
            {
                "time": r.collection_time.isoformat(),
                "moisture_10cm": r.moisture_10cm,
                "moisture_20cm": r.moisture_20cm,
                "moisture_40cm": r.moisture_40cm,
            }
            for r in records
        ]
    }


@router.get("/rainfall/latest")
async def get_latest_rainfall(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RainfallRecord).order_by(desc(RainfallRecord.collection_time)).limit(1))
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "rainfall": record.rainfall,
            "daily_rainfall": record.daily_rainfall,       # generic placeholder
        }
    }


@router.get("/runoff/latest")
async def get_latest_runoff(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunoffRecord).order_by(desc(RunoffRecord.collection_time)).limit(1))
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
    result = await db.execute(select(WaterLevelRecord).order_by(desc(WaterLevelRecord.collection_time)).limit(1))
    record = result.scalar_one_or_none()
    if not record:
        return {"data": None}
    return {
        "data": {
            "collection_time": record.collection_time.isoformat(),
            "water_level": record.water_level,
        }
    }


@router.get("/weather/daily")
async def get_weather_daily(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """逐日气象聚合：平均温度、平均湿度、日累计降雨"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(WeatherRecord)
        .where(WeatherRecord.collection_time >= since)
        .order_by(WeatherRecord.collection_time)
    )
    records = result.scalars().all()

    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "temps": [], "humidities": [], "rainfall": 0.0}
        if r.temperature is not None:
            daily[day]["temps"].append(r.temperature)
        if r.humidity is not None:
            daily[day]["humidities"].append(r.humidity)
        if r.rainfall is not None:
            daily[day]["rainfall"] += r.rainfall

    data = []
    for day, v in sorted(daily.items()):
        data.append({
            "date": day,
            "avg_temp": round(sum(v["temps"]) / len(v["temps"]), 1) if v["temps"] else None,
            "min_temp": round(min(v["temps"]), 1) if v["temps"] else None,
            "max_temp": round(max(v["temps"]), 1) if v["temps"] else None,
            "avg_humidity": round(sum(v["humidities"]) / len(v["humidities"]), 1) if v["humidities"] else None,
            "min_humidity": round(min(v["humidities"]), 1) if v["humidities"] else None,
            "max_humidity": round(max(v["humidities"]), 1) if v["humidities"] else None,
            "total_rainfall": round(v["rainfall"], 1),
        })
    return {"data": data}


@router.get("/weather/wind-rose")
async def get_wind_rose(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """风向频率分布（用于风玫瑰图）"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(WeatherRecord.wind_direction, WeatherRecord.wind_speed)
        .where(WeatherRecord.collection_time >= since)
        .where(WeatherRecord.wind_direction.isnot(None))
    )
    rows = result.all()

    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    
    freq: dict[str, int] = defaultdict(int)
    speed_sum: dict[str, float] = defaultdict(float)
    for wd, ws in rows:
        wd_str = wd
        try:
            deg = float(wd)
            idx = round(deg / 45.0) % 8
            wd_str = dirs[idx]
        except ValueError:
            wd_str = wd.replace('风', '')
            
        freq[wd_str] += 1
        speed_sum[wd_str] += (ws or 0)

    data = []
    total = sum(freq.values()) or 1
    for d in dirs:
        cnt = freq.get(d, 0)
        data.append({
            "direction": d,
            "count": cnt,
            "frequency": round(cnt / total * 100, 1) if total > 1 else (round(100.0, 1) if cnt > 0 else 0.0),
            "avg_speed": round(speed_sum[d] / cnt, 1) if cnt else 0,
        })
    return {"data": data}


@router.get("/soil/daily")
async def get_soil_daily(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """逐日土壤墒情聚合"""
    since = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(SoilRecord)
        .where(SoilRecord.collection_time >= since)
        .order_by(SoilRecord.collection_time)
    )
    records = result.scalars().all()

    daily: dict = {}
    for r in records:
        day = r.collection_time.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "m10": [], "m20": [], "m40": [], "n": [], "p": [], "k": [], "ph": [], "ec": []}
        if r.moisture_10cm is not None:
            daily[day]["m10"].append(r.moisture_10cm)
        if r.moisture_20cm is not None:
            daily[day]["m20"].append(r.moisture_20cm)
        if r.moisture_40cm is not None:
            daily[day]["m40"].append(r.moisture_40cm)
        if r.nitrogen is not None: daily[day]["n"].append(r.nitrogen)
        if r.phosphorus is not None: daily[day]["p"].append(r.phosphorus)
        if r.potassium is not None: daily[day]["k"].append(r.potassium)
        if r.ph is not None: daily[day]["ph"].append(r.ph)
        if r.conductivity is not None: daily[day]["ec"].append(r.conductivity)

    data = []
    for day, v in sorted(daily.items()):
        data.append({
            "date": day,
            "moisture_10cm": round(sum(v["m10"]) / len(v["m10"]), 1) if v["m10"] else None,
            "moisture_20cm": round(sum(v["m20"]) / len(v["m20"]), 1) if v["m20"] else None,
            "moisture_40cm": round(sum(v["m40"]) / len(v["m40"]), 1) if v["m40"] else None,
            "n": round(sum(v["n"])/len(v["n"]), 1) if v["n"] else None,
            "p": round(sum(v["p"])/len(v["p"]), 1) if v["p"] else None,
            "k": round(sum(v["k"])/len(v["k"]), 1) if v["k"] else None,
            "ph": round(sum(v["ph"])/len(v["ph"]), 1) if v["ph"] else None,
            "ec": round(sum(v["ec"])/len(v["ec"]), 1) if v["ec"] else None,
        })
    return {"data": data}

@router.get("/water_quality/daily")
async def get_wq_daily(days: int = Query(30, ge=7, le=90), db: AsyncSession = Depends(get_db)):
    since = datetime.now() - timedelta(days=days-1)
    from models import WaterQualityRecord
    result = await db.execute(select(WaterQualityRecord).where(WaterQualityRecord.collection_time >= since.replace(hour=0, minute=0, second=0)).order_by(WaterQualityRecord.collection_time))
    records = result.scalars().all()
    
    daily = defaultdict(lambda: {"cod": [], "tn": [], "tp": [], "nh4n": [], "ph": [], "do": [], "ec": [], "turb": [], "temp": []})
    for r in records:
        day = r.collection_time.date().isoformat()
        if r.cod is not None: daily[day]["cod"].append(r.cod)
        if r.total_nitrogen is not None: daily[day]["tn"].append(r.total_nitrogen)
        if r.total_phosphorus is not None: daily[day]["tp"].append(r.total_phosphorus)
        if r.ammonia_nitrogen is not None: daily[day]["nh4n"].append(r.ammonia_nitrogen)
        if r.ph is not None: daily[day]["ph"].append(r.ph)
        if r.dissolved_oxygen is not None: daily[day]["do"].append(r.dissolved_oxygen)
        if r.conductivity is not None: daily[day]["ec"].append(r.conductivity)
        if r.turbidity is not None: daily[day]["turb"].append(r.turbidity)
        if r.temperature is not None: daily[day]["temp"].append(r.temperature)
    
    res = []
    curr = since.date()
    today = datetime.now().date()
    while curr <= today:
        day = curr.isoformat()
        v = daily.get(day, {})
        res.append({
            "date": day,
            "cod": round(sum(v["cod"])/len(v["cod"]), 1) if v.get("cod") else None,
            "tn": round(sum(v["tn"])/len(v["tn"]), 2) if v.get("tn") else None,
            "tp": round(sum(v["tp"])/len(v["tp"]), 3) if v.get("tp") else None,
            "nh4n": round(sum(v["nh4n"])/len(v["nh4n"]), 2) if v.get("nh4n") else None,
            "ph": round(sum(v["ph"])/len(v["ph"]), 1) if v.get("ph") else None,
            "do": round(sum(v["do"])/len(v["do"]), 1) if v.get("do") else None,
            "ec": round(sum(v["ec"])/len(v["ec"]), 1) if v.get("ec") else None,
            "turbidity": round(sum(v["turb"])/len(v["turb"]), 1) if v.get("turb") else None,
            "water_temp": round(sum(v["temp"])/len(v["temp"]), 1) if v.get("temp") else None,
        })
        curr += timedelta(days=1)
    return {"data": res}

@router.get("/runoff/daily")
async def get_runoff_daily(days: int = Query(30, ge=7, le=90), db: AsyncSession = Depends(get_db)):
    since = datetime.now() - timedelta(days=days-1)
    from models import RunoffRecord
    result = await db.execute(select(RunoffRecord).where(RunoffRecord.collection_time >= since.replace(hour=0, minute=0, second=0)).order_by(RunoffRecord.collection_time))
    records = result.scalars().all()
    
    daily = defaultdict(lambda: {"sand": [], "flow": [], "speed": [], "total": [], "level": [], "rain": 0, "runoff": 0, "press": []})
    for r in records:
        day = r.collection_time.date().isoformat()
        if r.sand_content is not None: daily[day]["sand"].append(r.sand_content)
        if r.flow_rate is not None: daily[day]["flow"].append(r.flow_rate)
        if r.flow_speed is not None: daily[day]["speed"].append(r.flow_speed)
        if r.total_flow is not None: daily[day]["total"].append(r.total_flow)
        if r.water_level is not None: daily[day]["level"].append(r.water_level)
        if r.liquid_pressure is not None: daily[day]["press"].append(r.liquid_pressure)
        daily[day]["rain"] += (r.rainfall or 0)
        daily[day]["runoff"] += (r.runoff or 0)
    
    res = []
    curr = since.date()
    today = datetime.now().date()
    while curr <= today:
        day = curr.isoformat()
        v = daily.get(day, {})
        res.append({
            "date": day,
            "sand": round(sum(v["sand"])/len(v["sand"]), 2) if v.get("sand") else None,
            "flow": round(sum(v["flow"])/len(v["flow"]), 2) if v.get("flow") else None,
            "flow_speed": round(sum(v["speed"])/len(v["speed"]), 2) if v.get("speed") else None,
            "total_flow": round(max(v["total"]), 1) if v.get("total") else None,
            "water_level": round(sum(v["level"])/len(v["level"]), 2) if v.get("level") else None,
            "rainfall": round(v.get("rain", 0), 1),
            "runoff": round(v.get("runoff", 0), 1),
            "liquid_pressure": round(sum(v["press"])/len(v["press"]), 1) if v.get("press") else None,
        })
        curr += timedelta(days=1)
    return {"data": res}
