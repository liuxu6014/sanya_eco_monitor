from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import InsectRecord, RunoffRecord, SporeRecord, WaterQualityRecord
from services.weather_support import get_weather_support
from services.warning_rules import build_warning_analysis, derive_pest_risk_level


RUNOFF_DEVICE_NAMES = {
    "16132920": "芒果林径流点 1",
    "16132921": "橡胶林径流点 1",
    "16132922": "次生林径流点",
    "16132923": "芒果林径流点 2",
    "16132924": "橡胶林径流点 2",
    "16132925": "槟榔林径流点",
}

WATER_METRICS = (
    ("ammonia_nitrogen", "氨氮", "mg/L"),
    ("total_phosphorus", "总磷", "mg/L"),
    ("total_nitrogen", "总氮", "mg/L"),
    ("permanganate_index", "高锰酸盐指数（按 COD 替代表达）", "mg/L"),
)


def _avg(values: list[float | None], ndigits: int = 3) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), ndigits)


def _safe_pct(base: float | None, current: float | None, ndigits: int = 1) -> float | None:
    if base in (None, 0) or current is None:
        return None
    return round((base - current) / base * 100, ndigits)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _day_gap(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        start_day = datetime.strptime(start, "%Y-%m-%d").date()
        end_day = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return None
    return abs((end_day - start_day).days)


def _risk_level(insect_peak: int, spore_peak: int) -> str:
    if (
        insect_peak >= settings.GUIDELINE_INSECT_WARNING_THRESHOLD
        or spore_peak >= settings.GUIDELINE_SPORE_WARNING_THRESHOLD
    ):
        return "高"
    if (
        insect_peak >= max(1, settings.GUIDELINE_INSECT_WARNING_THRESHOLD // 2)
        or spore_peak >= max(1, settings.GUIDELINE_SPORE_WARNING_THRESHOLD // 2)
    ):
        return "中"
    return "低"


async def _build_water_quality_metrics(
    db: AsyncSession,
    *,
    recent_days: int,
) -> dict[str, Any]:
    water_code = settings.WATER_QUALITY_CODE.strip() or "16133028"

    first_result = await db.execute(
        select(WaterQualityRecord)
        .where(WaterQualityRecord.device_code == water_code)
        .order_by(asc(WaterQualityRecord.collection_time))
        .limit(1)
    )
    first_record = first_result.scalar_one_or_none()
    if not first_record:
        return {
            "available": False,
            "message": "暂无水质数据，无法计算基准期与削减率。",
        }

    now = datetime.now()
    baseline_start = first_record.collection_time
    baseline_days = min(
        settings.GUIDELINE_BASELINE_DAYS,
        max(1, (now.date() - baseline_start.date()).days + 1),
    )
    baseline_end = baseline_start + timedelta(days=baseline_days - 1)
    recent_start = now - timedelta(days=recent_days - 1)

    baseline_result = await db.execute(
        select(WaterQualityRecord).where(
            WaterQualityRecord.device_code == water_code,
            WaterQualityRecord.collection_time >= baseline_start,
            WaterQualityRecord.collection_time <= baseline_end,
        )
    )
    recent_result = await db.execute(
        select(WaterQualityRecord).where(
            WaterQualityRecord.device_code == water_code,
            WaterQualityRecord.collection_time >= recent_start,
        )
    )
    latest_result = await db.execute(
        select(WaterQualityRecord)
        .where(WaterQualityRecord.device_code == water_code)
        .order_by(desc(WaterQualityRecord.collection_time))
        .limit(1)
    )

    baseline_records = baseline_result.scalars().all()
    recent_records = recent_result.scalars().all()
    latest_record = latest_result.scalar_one_or_none()

    metrics: list[dict[str, Any]] = []
    reduction_values: list[float] = []

    for field_name, label, unit in WATER_METRICS:
        baseline_avg = _avg([getattr(record, field_name) for record in baseline_records])
        recent_avg = _avg([getattr(record, field_name) for record in recent_records])
        latest_value = getattr(latest_record, field_name) if latest_record else None
        recent_reduction = _safe_pct(baseline_avg, recent_avg)
        latest_reduction = _safe_pct(baseline_avg, latest_value)
        if recent_reduction is not None:
            reduction_values.append(recent_reduction)

        metrics.append(
            {
                "field": field_name,
                "label": label,
                "unit": unit,
                "baseline_avg": baseline_avg,
                "recent_avg": recent_avg,
                "latest_value": round(latest_value, 3) if latest_value is not None else None,
                "recent_reduction_rate": recent_reduction,
                "latest_reduction_rate": latest_reduction,
            }
        )

    valid_metrics = [item for item in metrics if item["recent_reduction_rate"] is not None]
    best_metric = max(valid_metrics, key=lambda item: item["recent_reduction_rate"]) if valid_metrics else None
    worst_metric = min(valid_metrics, key=lambda item: item["recent_reduction_rate"]) if valid_metrics else None
    improved_metrics_count = sum(1 for item in valid_metrics if (item["recent_reduction_rate"] or 0) >= 0)
    degraded_metrics_count = sum(1 for item in valid_metrics if (item["recent_reduction_rate"] or 0) < 0)

    return {
        "available": True,
        "device_code": water_code,
        "baseline_period": {
            "start": baseline_start.date().isoformat(),
            "end": baseline_end.date().isoformat(),
            "days": baseline_days,
            "records_count": len(baseline_records),
            "note": "系统统一以设备接入后的前 30 天均值作为基准期；不足 30 天时按已有天数计算。",
        },
        "recent_period": {
            "start": recent_start.date().isoformat(),
            "end": now.date().isoformat(),
            "days": recent_days,
            "records_count": len(recent_records),
        },
        "metrics": metrics,
        "metrics_count": len(metrics),
        "improved_metrics_count": improved_metrics_count,
        "degraded_metrics_count": degraded_metrics_count,
        "best_metric": best_metric,
        "worst_metric": worst_metric,
        "composite_reduction_rate": round(sum(reduction_values) / len(reduction_values), 1) if reduction_values else None,
        "latest_collection_time": _iso(latest_record.collection_time if latest_record else None),
    }


async def _build_runoff_metrics(
    db: AsyncSession,
    *,
    recent_days: int,
) -> dict[str, Any]:
    def _avg_raw(values: list[float | None]) -> float | None:
        clean = [value for value in values if value is not None]
        if not clean:
            return None
        return sum(clean) / len(clean)

    recent_start = datetime.now() - timedelta(days=recent_days - 1)
    result = await db.execute(
        select(RunoffRecord)
        .where(RunoffRecord.collection_time >= recent_start)
        .order_by(RunoffRecord.collection_time)
    )
    records = result.scalars().all()
    if not records:
        return {
            "available": False,
            "message": "暂无径流数据，无法计算水土流失监测型指标。",
        }

    grouped: dict[str, dict[str, list[float | None]]] = defaultdict(
        lambda: {
            "flow": [],
            "runoff": [],
            "sand": [],
            "rain": [],
        }
    )
    for record in records:
        bucket = grouped[record.device_code]
        bucket["flow"].append(record.flow_rate)
        bucket["runoff"].append(record.runoff)
        bucket["sand"].append(record.sand_content)
        bucket["rain"].append(record.rainfall)

    station_metrics: list[dict[str, Any]] = []
    reference_code = settings.GUIDELINE_REFERENCE_RUNOFF_CODE.strip() or "16132922"
    for device_code, bucket in grouped.items():
        avg_runoff_raw = _avg_raw(bucket["runoff"])
        avg_flow_raw = _avg_raw(bucket["flow"])
        avg_sand_raw = _avg_raw(bucket["sand"])
        avg_rain_raw = _avg_raw(bucket["rain"])
        runoff_factor = avg_runoff_raw if avg_runoff_raw not in (None, 0) else avg_flow_raw
        raw_erosion_proxy = (runoff_factor or 0) * (avg_sand_raw or 0)
        station_metrics.append(
            {
                "device_code": device_code,
                "name": RUNOFF_DEVICE_NAMES.get(device_code, device_code),
                "avg_runoff": round(avg_runoff_raw, 4) if avg_runoff_raw is not None else None,
                "avg_flow_rate": round(avg_flow_raw, 4) if avg_flow_raw is not None else None,
                "avg_sand_content": round(avg_sand_raw, 4) if avg_sand_raw is not None else None,
                "avg_rainfall": round(avg_rain_raw, 3) if avg_rain_raw is not None else None,
                "erosion_proxy": round(raw_erosion_proxy, 4),
                "_raw_erosion_proxy": raw_erosion_proxy,
            }
        )

    station_metrics.sort(key=lambda item: item["_raw_erosion_proxy"], reverse=True)
    reference_station = next((item for item in station_metrics if item["device_code"] == reference_code), None)
    reference_proxy_raw = reference_station["_raw_erosion_proxy"] if reference_station else None

    comparison_values = [
        item["_raw_erosion_proxy"]
        for item in station_metrics
        if item["device_code"] != reference_code
    ]
    plantation_avg_proxy_raw = sum(comparison_values) / len(comparison_values) if comparison_values else None
    avg_erosion_proxy_raw = _avg_raw([item["_raw_erosion_proxy"] for item in station_metrics])
    avg_rainfall = _avg([item["avg_rainfall"] for item in station_metrics], ndigits=3)
    if plantation_avg_proxy_raw is None or reference_proxy_raw is None:
        estimated_reduction_rate = None
    elif plantation_avg_proxy_raw == 0:
        estimated_reduction_rate = 0.0 if reference_proxy_raw == 0 else None
    else:
        estimated_reduction_rate = round((plantation_avg_proxy_raw - reference_proxy_raw) / plantation_avg_proxy_raw * 100, 1)

    plantation_avg_proxy = round(plantation_avg_proxy_raw, 4) if plantation_avg_proxy_raw is not None else None
    avg_erosion_proxy = round(avg_erosion_proxy_raw, 4) if avg_erosion_proxy_raw is not None else None
    reference_gap = (
        round(plantation_avg_proxy_raw - reference_proxy_raw, 4)
        if plantation_avg_proxy_raw is not None and reference_proxy_raw is not None
        else None
    )

    for item in station_metrics:
        if reference_proxy_raw in (None, 0):
            item["relative_to_reference"] = None
        else:
            item["relative_to_reference"] = round((item["_raw_erosion_proxy"] / reference_proxy_raw - 1) * 100, 1)

    valid_stations = [item for item in station_metrics if item["erosion_proxy"] is not None]
    highest_risk_station = valid_stations[0] if valid_stations else None
    lowest_risk_station = valid_stations[-1] if valid_stations else None

    for item in station_metrics:
        item.pop("_raw_erosion_proxy", None)

    return {
        "available": True,
        "period_days": recent_days,
        "station_count": len(station_metrics),
        "reference_station": reference_station,
        "plantation_avg_proxy": plantation_avg_proxy,
        "avg_erosion_proxy": avg_erosion_proxy,
        "avg_rainfall": avg_rainfall,
        "estimated_reduction_rate": estimated_reduction_rate,
        "reference_gap": reference_gap,
        "highest_risk_station": highest_risk_station,
        "lowest_risk_station": lowest_risk_station,
        "station_metrics": station_metrics,
        "note": "以次生林为参照样地，按径流或流量与含沙量构建监测型侵蚀压力代理指标。",
    }


async def _build_pest_management_metrics(
    db: AsyncSession,
    *,
    recent_days: int,
) -> dict[str, Any]:
    recent_start = datetime.now() - timedelta(days=recent_days - 1)

    insect_result = await db.execute(
        select(InsectRecord)
        .where(InsectRecord.collection_time >= recent_start)
        .order_by(InsectRecord.collection_time)
    )
    spore_result = await db.execute(
        select(SporeRecord)
        .where(SporeRecord.collection_time >= recent_start)
        .order_by(SporeRecord.collection_time)
    )
    insect_records = insect_result.scalars().all()
    spore_records = spore_result.scalars().all()

    insect_daily: dict[str, int] = defaultdict(int)
    insect_species: dict[str, int] = defaultdict(int)
    for record in insect_records:
        day = record.collection_time.strftime("%Y-%m-%d")
        insect_daily[day] += record.total_count
        for name, count in (record.species_data or {}).items():
            insect_species[name] += int(count)

    spore_daily: dict[str, int] = defaultdict(int)
    for record in spore_records:
        day = record.collection_time.strftime("%Y-%m-%d")
        spore_daily[day] += record.total_count

    peak_insect_day, peak_insect_count = ("—", 0)
    if insect_daily:
        peak_insect_day, peak_insect_count = max(insect_daily.items(), key=lambda item: item[1])

    peak_spore_day, peak_spore_count = ("—", 0)
    if spore_daily:
        peak_spore_day, peak_spore_count = max(spore_daily.items(), key=lambda item: item[1])

    top_species_name = "未识别"
    top_species_count = 0
    if insect_species:
        top_species_name, top_species_count = max(insect_species.items(), key=lambda item: item[1])

    total_insects = sum(insect_daily.values())
    total_spores = sum(spore_daily.values())
    active_insect_days = len(insect_daily)
    active_spore_days = len(spore_daily)
    species_count = len(insect_species)
    dominant_species_share = round(top_species_count / total_insects * 100, 1) if total_insects else None
    peak_gap_days = _day_gap(
        peak_insect_day if peak_insect_day != "—" else None,
        peak_spore_day if peak_spore_day != "—" else None,
    )

    risk_level = derive_pest_risk_level(peak_insect_count, peak_spore_count)
    if risk_level == "高":
        suggestion = "建议同步开展田间复核、重点虫种排查和病虫风险处置。"
    elif risk_level == "中":
        suggestion = "建议提高巡检频率，并持续跟踪孢子波动。"
    else:
        suggestion = "当前病虫风险总体平稳，建议维持例行监测。"

    chain_text = (
        f"最近{recent_days}天内，虫情峰值出现在{peak_insect_day}，当日捕获{peak_insect_count}只；"
        f"孢子峰值出现在{peak_spore_day}，当日捕获{peak_spore_count}个；"
        f"重点关注虫种为{top_species_name}。{suggestion}"
    )

    return {
        "available": True,
        "period_days": recent_days,
        "risk_level": risk_level,
        "total_insects": total_insects,
        "total_spores": total_spores,
        "avg_daily_insects": round(total_insects / active_insect_days, 1) if active_insect_days else None,
        "avg_daily_spores": round(total_spores / active_spore_days, 1) if active_spore_days else None,
        "active_insect_days": active_insect_days,
        "active_spore_days": active_spore_days,
        "species_count": species_count,
        "top_species": {
            "name": top_species_name,
            "count": top_species_count,
            "share": dominant_species_share,
        },
        "insect_peak": {
            "date": peak_insect_day,
            "count": peak_insect_count,
        },
        "spore_peak": {
            "date": peak_spore_day,
            "count": peak_spore_count,
        },
        "peak_gap_days": peak_gap_days,
        "suggestion": suggestion,
        "chain_text": chain_text,
        "management_record_template": (
            "系统监测到风险指标升高后，可自动生成预警建议，并在月报中固化“预警时间、风险对象、建议动作、结果复核”的闭环描述。"
        ),
    }


async def build_guideline_metrics(
    db: AsyncSession,
    *,
    recent_days: int | None = None,
) -> dict[str, Any]:
    recent_days = recent_days or settings.GUIDELINE_RECENT_DAYS
    weather_support = await get_weather_support()
    water_quality = await _build_water_quality_metrics(db, recent_days=recent_days)
    runoff_erosion = await _build_runoff_metrics(db, recent_days=recent_days)
    pest_management = await _build_pest_management_metrics(db, recent_days=recent_days)
    warning_analysis = build_warning_analysis(
        recent_days=recent_days,
        pest_management=pest_management,
        runoff_erosion=runoff_erosion,
        weather_support=weather_support,
    )

    history_summary = weather_support.get("history_summary") or {}
    history_range = weather_support.get("history_range") or {}
    weather_enabled = weather_support.get("enabled") and weather_support.get("status") == "ok"

    climate_message = ""

    composite_reduction = water_quality.get("composite_reduction_rate")
    erosion_reduction = runoff_erosion.get("estimated_reduction_rate")
    pest_risk = pest_management.get("risk_level", "—")
    insect_peak = pest_management.get("insect_peak", {}) or {}

    methodology = {
        "monitoring_statement": (
            "本项目围绕水土流失、农业面源污染和病虫害等关键风险，构建了覆盖径流、雨量、水质、虫情和孢子的在线监测网络，"
            "可对不同生态样地开展对照分析。"
        ),
        "baseline_statement": (
            "农田排水水质指标统一以设备接入后的前30天均值作为系统基准期；若当前不足30天，则按已有天数计算，"
            "满30天后固定按首30天口径计算削减率。"
        ),
    }

    implementation_matrix = {
        "current_foundation": [
            {
                "name": "地表径流监测",
                "status": "已有",
                "detail": "已接入次生林、橡胶林、芒果林等监测点，可用于径流、雨量与含沙分析。",
            },
            {
                "name": "雨量监测",
                "status": "已有",
                "detail": "可作为水土流失与水源涵养支撑分析输入。",
            },
            {
                "name": "农田排水水质监测",
                "status": "已有",
                "detail": "当前有效指标包括氨氮、总磷、总氮与高锰酸盐指数（按 COD 替代表达）。",
            },
            {
                "name": "虫情与孢子监测",
                "status": "已有",
                "detail": "可获取虫种、日期、数量和时间序列，用于趋势分析与风险研判。",
            },
            {
                "name": "历史数据积累",
                "status": "部分已有",
                "detail": "当前已支持近30天趋势分析，多年尺度基准数据仍需补充。",
            },
            {
                "name": "气象补充参数",
                "status": weather_enabled and "已补充" or "部分补充",
                "detail": weather_enabled
                and "已接入最近7天历史气温、湿度、降水与风速，可做监测型支撑分析；正式蒸散发参数仍不足。"
                or "当前缺少稳定历史气象补充，蒸散发与多年对比暂不具备。",
            },
        ],
        "deliverable_items": [
            {
                "index": "7.1",
                "name": "水土流失强度减少率",
                "status": "可做",
                "result": erosion_reduction is not None and f"估算减蚀率 {erosion_reduction}%" or "已具备计算条件",
                "method": "以次生林为参照，按径流或流量乘含沙量构建监测型侵蚀代理指标。",
            },
            {
                "index": "7.3",
                "name": "农业面源污染削减率",
                "status": "可做",
                "result": composite_reduction is not None and f"综合削减率 {composite_reduction}%" or "已具备阶段计算条件",
                "method": "按统一基准期计算各水质指标近30天均值与削减率。",
            },
            {
                "index": "7.8",
                "name": "病虫发生情况",
                "status": "可做",
                "result": f"当前风险等级 {pest_risk}，虫情峰值 {insect_peak.get('date', '—')}",
                "method": "基于虫情峰值、孢子峰值和阈值规则生成趋势判断与预警建议。",
            },
            {
                "index": "8.1",
                "name": "工程尺度水土流失强度减少率",
                "status": "可做",
                "result": "沿用现有径流监测网络形成项目区对照结果。",
                "method": "以当前项目区监测网络作为工程尺度支撑，输出区域治理减蚀评估。",
            },
            {
                "index": "8.3",
                "name": "工程尺度农业面源污染削减率",
                "status": "可做",
                "result": "沿用现有4项水质指标形成阶段性削减评估。",
                "method": "基于统一基准期口径输出项目阶段削减结果。",
            },
        ],
        "support_items": [
            {
                "index": "7.2",
                "name": "生态系统水源涵养能力提升率",
                "status": "补强后可升级",
                "current_mode": weather_enabled and "可输出历史气象 + 降雨 + 径流支撑分析" or "当前仅可输出降雨 + 径流监测分析",
                "needed": "仍需生态系统面积、蒸散发参数和多年气象资料。",
            },
            {
                "index": "7.6",
                "name": "污染削减能力提升率",
                "status": "补强后可升级",
                "current_mode": "当前可做浓度改善率和阶段削减效果，不做严格负荷削减。",
                "needed": "仍需治理前基线、入流出流断面和对应流量数据。",
            },
            {
                "index": "8.2",
                "name": "工程尺度水源涵养能力提升率",
                "status": "补强后可升级",
                "current_mode": weather_enabled and "可输出工程期历史气象支撑判断" or "当前仅能输出项目期监测型支撑判断",
                "needed": "仍需生态系统面积、蒸散发参数和多年气象资料。",
            },
        ],
        "management_closure": [
            {
                "name": "病虫风险逻辑链条",
                "status": "部分具备",
                "current": "系统已可生成“监测发现 - 风险判断 - 处置建议”的段落。",
                "needed": "仍需补充病虫映射关系、预警阈值、处置记录和复核结果。",
            },
            {
                "name": "适应性管理记录",
                "status": "部分具备",
                "current": "系统已可生成预警与建议动作描述。",
                "needed": "仍需补充预警时间、处置措施、责任单位和复核结果台账。",
            },
            {
                "name": "监测体系科学性说明",
                "status": "已具备",
                "current": "已可在报告中固定输出监测点布设、监测对象、监测频率和在线化能力说明。",
                "needed": "保持统一模板即可。",
            },
        ],
        "confirmed_rules": [
            "高锰酸盐指数统一按 COD 替代表达。",
            "水质基准期统一按设备接入后的前30天均值计算；不足30天时按已有天数先算，满30天后固定按首30天口径。",
            "当前无直接数据支撑的指标，本期前端与报告均不展示承诺值。",
        ],
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "recent_days": recent_days,
        "water_quality": water_quality,
        "runoff_erosion": runoff_erosion,
        "pest_management": pest_management,
        "warning_analysis": warning_analysis,
        "weather_support": weather_support,
        "water_source_support": {
            "status": "partial" if weather_enabled else "limited",
            "message": climate_message,
        },
        "methodology": methodology,
        "implementation_matrix": implementation_matrix,
        "analytics_summary": {
            "weather": {
                "range": history_range,
                "summary": history_summary,
            },
            "water_quality": {
                "composite_reduction_rate": composite_reduction,
                "best_metric": water_quality.get("best_metric"),
                "worst_metric": water_quality.get("worst_metric"),
                "improved_metrics_count": water_quality.get("improved_metrics_count"),
                "degraded_metrics_count": water_quality.get("degraded_metrics_count"),
            },
            "runoff": {
                "estimated_reduction_rate": erosion_reduction,
                "station_count": runoff_erosion.get("station_count"),
                "highest_risk_station": runoff_erosion.get("highest_risk_station"),
                "lowest_risk_station": runoff_erosion.get("lowest_risk_station"),
                "avg_erosion_proxy": runoff_erosion.get("avg_erosion_proxy"),
            },
            "pest": {
                "risk_level": pest_risk,
                "total_insects": pest_management.get("total_insects"),
                "total_spores": pest_management.get("total_spores"),
                "species_count": pest_management.get("species_count"),
                "peak_gap_days": pest_management.get("peak_gap_days"),
            },
            "warnings": warning_analysis.get("summary"),
        },
    }
