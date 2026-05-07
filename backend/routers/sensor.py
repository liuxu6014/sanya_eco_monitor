from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import RainfallRecord, RunoffRecord, WaterLevelRecord
from services.water_quality_support import get_water_quality_records, resolve_water_quality_codes


router = APIRouter(prefix="/api/sensor", tags=["传感器"])


def _avg(values: list[float | None]) -> float | None:
    valid = [float(value) for value in values if value is not None]
    return round(sum(valid) / len(valid), 2) if valid else None


def _max_item(items: list[dict], key: str) -> dict:
    return max(items, key=lambda item: item.get(key) or 0, default={})


def _trend_direction(values: list[float]) -> str:
    if len(values) < 2:
        return "数据不足"
    first = values[0]
    last = values[-1]
    if last > first * 1.1:
        return "上升"
    if last < first * 0.9:
        return "下降"
    return "平稳"


def _month_label(date_text: str) -> str:
    return date_text[:7]


def _year_label(date_text: str) -> str:
    return date_text[:4]


def _sum_by_period(items: list[dict], value_key: str, label_fn) -> list[dict]:
    buckets = defaultdict(float)
    for item in items:
        buckets[label_fn(item["date"])] += item.get(value_key) or 0
    return [{"date": key, "value": round(value, 2)} for key, value in sorted(buckets.items())]


def _rainfall_analysis_text(days: int, total: float, rainy_days: int, peak: dict, max_hourly: dict, station_peak: dict, direction: str, level: str) -> str:
    return (
        f"近{days}天区域累计降雨{total}mm，雨日{rainy_days}天，整体降雨过程呈{direction}态势，当前等级判断为{level}。"
        f"区域单日峰值为{peak.get('rainfall', 0)}mm，出现在{peak.get('date') or '暂无'}；"
        f"站点最大读数为{station_peak.get('station_peak', 0)}mm，最大小时雨量为{max_hourly.get('max_hourly', 0)}mm。"
        "从监测意义看，雨日较少但单站峰值仍需与径流、含沙量联动核查，防止局部短历时降雨造成坡面冲刷或排水口淤积。"
        "后续建议在降雨前检查雨量计通讯和排水通道，降雨后优先核查低洼地块、裸露坡面、排水出口和径流监测点，形成雨量-径流-含沙的闭环记录。"
    )


def _runoff_analysis_text(days: int, total_runoff: float, avg_sand: float | None, avg_flow: float | None, peak_runoff: dict, peak_sand: dict, peak_erosion: dict, trend: str, risk_level: str) -> str:
    return (
        f"近{days}天地表径流累计{total_runoff}m³，平均流量{avg_flow if avg_flow is not None else '暂无'}m³/s，"
        f"平均含沙量{avg_sand if avg_sand is not None else '暂无'}kg/L，径流变化趋势为{trend}，综合判断为{risk_level}。"
        f"径流峰值出现在{peak_runoff.get('date') or '暂无'}，峰值为{peak_runoff.get('runoff', 0)}m³；"
        f"含沙量峰值出现在{peak_sand.get('date') or '暂无'}，侵蚀代理峰值出现在{peak_erosion.get('date') or '暂无'}。"
        "分析上应重点关注径流峰值与含沙峰值是否同步出现：若同步升高，说明降雨或排水过程可能已经携带较多泥沙；若径流升高但含沙不高，则以排水能力和沟道通畅性核查为主。"
        "建议对峰值日期对应站点开展现场复核，检查坡面覆盖、截排水设施、沉砂设施和沟道淤积情况，并把异常点纳入后续治理清单。"
    )


def _water_quality_analysis_text(days: int, metric_summary: list[dict], main_risk: dict | None, risk_level: str, risk_score: int) -> str:
    exceed_total = sum(item.get("exceed_days") or 0 for item in metric_summary)
    metric_text = "、".join(
        f"{item['label']}均值{item['avg'] if item['avg'] is not None else '暂无'}{item['unit']}，超标{item['exceed_days']}天"
        for item in metric_summary
    )
    main_label = main_risk["label"] if main_risk else "暂无明确指标"
    return (
        f"近{days}天面源水质污染综合评分为{risk_score}分，风险等级为{risk_level}，当前重点指标为{main_label}。"
        f"本期各指标表现为：{metric_text}。"
        f"累计超标天数为{exceed_total}天，说明水质风险需要结合降雨、径流和农田排水过程进行联动判断。"
        "若氮磷指标持续偏高，应优先排查施肥时段、地表径流路径、沟渠汇入口和生态缓冲带完整性；若高锰酸盐指数或氨氮升高，则需关注有机污染输入和局部排水滞留。"
        "建议后续把高值日期与雨量、径流峰值进行比对，必要时增加采样频次，并形成问题点位、可能来源和处置措施的台账。"
    )


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


@router.get("/rainfall/daily")
async def get_rainfall_daily(
    days: int = Query(30, ge=1, le=366),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now().date() - timedelta(days=days - 1)
    result = await db.execute(
        select(RainfallRecord)
        .where(RainfallRecord.collection_time >= datetime.combine(since, datetime.min.time()))
        .order_by(RainfallRecord.collection_time)
    )
    records = result.scalars().all()
    station_daily = defaultdict(lambda: defaultdict(lambda: {"rainfall": 0.0, "max_hourly": 0.0, "records": 0}))
    for record in records:
        day = record.collection_time.date().isoformat()
        rainfall = record.rainfall if record.rainfall is not None else record.daily_rainfall
        hourly = record.hourly_rainfall if record.hourly_rainfall is not None else record.rainfall
        bucket = station_daily[day][record.device_code]
        # 雨量计返回的是采集时刻的累计读数，不能把 5 分钟采集值逐条累加。
        bucket["rainfall"] = max(bucket["rainfall"], rainfall or 0)
        bucket["max_hourly"] = max(bucket["max_hourly"], hourly or 0)
        bucket["records"] += 1

    items = []
    current = since
    today = datetime.now().date()
    while current <= today:
        day = current.isoformat()
        station_values = list(station_daily.get(day, {}).values())
        rainfall_values = [value["rainfall"] for value in station_values]
        hourly_values = [value["max_hourly"] for value in station_values]
        regional_rainfall = (
            round(sum(rainfall_values) / len(rainfall_values), 1)
            if rainfall_values
            else 0
        )
        items.append(
            {
                "date": day,
                "rainfall": regional_rainfall,
                "max_hourly": round(max(hourly_values), 1) if hourly_values else 0,
                "station_peak": round(max(rainfall_values), 1) if rainfall_values else 0,
                "station_count": len(station_values),
                "records": sum(value["records"] for value in station_values),
            }
        )
        current += timedelta(days=1)
    return {"data": items}


@router.get("/rainfall/analysis")
async def get_rainfall_analysis(
    days: int = Query(30, ge=7, le=366),
    db: AsyncSession = Depends(get_db),
):
    daily_result = await get_rainfall_daily(days=days, db=db)
    daily = daily_result.get("data", [])
    values = [float(item.get("rainfall") or 0) for item in daily]
    total = round(sum(values), 1)
    peak = _max_item(daily, "rainfall")
    max_hourly = _max_item(daily, "max_hourly")
    station_peak = _max_item(daily, "station_peak")
    rainy_days = len([value for value in values if value > 0])
    avg = round(total / max(days, 1), 1)
    direction = _trend_direction(values[-7:] if len(values) >= 7 else values)
    peak_value = peak.get("rainfall") or 0
    level = "强降雨关注" if peak_value >= 50 else "中到大雨关注" if peak_value >= 25 else "小雨过程" if peak_value > 0 else "常规监测"
    analysis = _rainfall_analysis_text(days, total, rainy_days, peak, max_hourly, station_peak, direction, level)
    strategy = [
        "雨前复核雨量计、径流沟渠和排水口，保证降雨过程数据连续。",
        "雨后重点查看坡面裸露区、低洼地块和排水出口，联动关注径流与含沙变化。",
        "单日区域雨量超过25mm时加密巡查；超过50mm时启动重点地块防冲刷检查。",
    ]
    return {
        "data": {
            "period_days": days,
            "daily": daily,
            "monthly": _sum_by_period(daily, "rainfall", _month_label),
            "yearly": _sum_by_period(daily, "rainfall", _year_label),
            "summary": {
                "total_rainfall": total,
                "avg_daily": avg,
                "rainy_days": rainy_days,
                "peak_date": peak.get("date"),
                "peak_rainfall": peak.get("rainfall", 0),
                "max_hourly_date": max_hourly.get("date"),
                "max_hourly": max_hourly.get("max_hourly", 0),
                "station_peak_date": station_peak.get("date"),
                "station_peak": station_peak.get("station_peak", 0),
                "trend": direction,
                "level": level,
                "analysis": analysis,
            },
            "strategy": strategy,
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
    configured_code = settings.WATER_QUALITY_CODE.strip() or "16133028"
    start_dt = since.replace(hour=0, minute=0, second=0, microsecond=0)
    codes = await resolve_water_quality_codes(
        db,
        preferred_code=configured_code,
        start_dt=start_dt,
    )
    records = await get_water_quality_records(
        db,
        start_dt=start_dt,
        codes=codes,
    )

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


@router.get("/runoff/analysis")
async def get_runoff_analysis(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    daily_result = await get_runoff_daily(days=days, db=db)
    daily = daily_result.get("data", [])
    runoff_values = [float(item.get("runoff") or 0) for item in daily]
    sand_values = [float(item.get("sand") or 0) for item in daily if item.get("sand") is not None]
    flow_values = [float(item.get("flow") or 0) for item in daily if item.get("flow") is not None]
    erosion_series = [
        {
            "date": item["date"],
            "value": round((item.get("runoff") or 0) * (item.get("sand") or 0), 2),
        }
        for item in daily
    ]
    peak_runoff = _max_item(daily, "runoff")
    peak_sand = _max_item(daily, "sand")
    peak_erosion = _max_item(erosion_series, "value")
    avg_sand = _avg(sand_values)
    avg_flow = _avg(flow_values)
    total_runoff = round(sum(runoff_values), 1)
    trend = _trend_direction(runoff_values[-7:] if len(runoff_values) >= 7 else runoff_values)
    risk_score = min(100, round((avg_sand or 0) * 30 + total_runoff / max(days, 1) * 8))
    risk_level = "高风险" if risk_score >= 70 else "重点关注" if risk_score >= 40 else "常规监测"
    analysis = _runoff_analysis_text(days, total_runoff, avg_sand, avg_flow, peak_runoff, peak_sand, peak_erosion, trend, risk_level)
    return {
        "data": {
            "period_days": days,
            "daily": daily,
            "erosion_series": erosion_series,
            "summary": {
                "total_runoff": total_runoff,
                "avg_sand": avg_sand,
                "avg_flow": avg_flow,
                "peak_runoff_date": peak_runoff.get("date"),
                "peak_runoff": peak_runoff.get("runoff", 0),
                "peak_sand_date": peak_sand.get("date"),
                "peak_sand": peak_sand.get("sand"),
                "peak_erosion_date": peak_erosion.get("date"),
                "peak_erosion_proxy": peak_erosion.get("value", 0),
                "trend": trend,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "analysis": analysis,
            },
            "strategy": [
                "强降雨前检查坡面覆盖、排水沟和沉砂设施，减少裸露地表直接冲刷。",
                "含沙量或径流量峰值后，优先巡查峰值日期对应区域，核查沟蚀、面蚀和排口淤积。",
                "连续上升时建议临时加密监测频次，并对裸露坡面采取覆盖、拦挡和植被恢复措施。",
            ],
        }
    }


@router.get("/water_quality/analysis")
async def get_water_quality_analysis(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    daily_result = await get_wq_daily(days=days, db=db)
    daily = daily_result.get("data", [])
    metrics = {
        "permanganate": {"label": "高锰酸盐指数", "unit": "mg/L", "limit": 6.0},
        "tn": {"label": "总氮", "unit": "mg/L", "limit": 1.0},
        "tp": {"label": "总磷", "unit": "mg/L", "limit": 0.2},
        "nh4n": {"label": "氨氮", "unit": "mg/L", "limit": 1.0},
    }
    metric_summary = []
    for key, meta in metrics.items():
        values = [float(item[key]) for item in daily if item.get(key) is not None]
        avg_value = _avg(values)
        max_value = max(values) if values else None
        exceed_days = len([value for value in values if value > meta["limit"]])
        metric_summary.append(
            {
                "key": key,
                "label": meta["label"],
                "unit": meta["unit"],
                "limit": meta["limit"],
                "avg": avg_value,
                "max": round(max_value, 3) if max_value is not None else None,
                "exceed_days": exceed_days,
                "trend": _trend_direction(values[-7:] if len(values) >= 7 else values),
            }
        )
    degraded = sorted(metric_summary, key=lambda item: (item["exceed_days"], item["max"] or 0), reverse=True)
    main_risk = degraded[0] if degraded else None
    risk_score = min(100, sum(item["exceed_days"] for item in metric_summary) * 6)
    risk_level = "高风险" if risk_score >= 70 else "重点关注" if risk_score >= 30 else "常规监测"
    analysis = _water_quality_analysis_text(days, metric_summary, main_risk, risk_level, risk_score)
    return {
        "data": {
            "period_days": days,
            "daily": daily,
            "metrics": metric_summary,
            "summary": {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "main_risk": main_risk["label"] if main_risk else None,
                "main_risk_exceed_days": main_risk["exceed_days"] if main_risk else 0,
                "analysis": analysis,
            },
            "strategy": [
                "降雨后重点核查农田排水口和沟渠交汇处，关注氮磷指标短时升高。",
                "对总氮、总磷连续偏高区域，优先排查施肥时段、地表径流路径和缓冲带完整性。",
                "建议结合雨量与径流数据开展联动判断，必要时增加采样频次并形成溯源记录。",
            ],
        }
    }
