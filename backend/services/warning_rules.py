from __future__ import annotations

from typing import Any

from config import settings


LEVELS = (
    {"code": "normal", "label": "正常", "tone": "neutral", "color": "#38bdf8"},
    {"code": "attention", "label": "关注", "tone": "watch", "color": "#facc15"},
    {"code": "severe", "label": "较严重", "tone": "warning", "color": "#fb7185"},
    {"code": "high", "label": "高等级", "tone": "danger", "color": "#f97316"},
    {"code": "critical", "label": "极高", "tone": "critical", "color": "#ef4444"},
)


def _parse_thresholds(raw: str, defaults: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    try:
        parts = [float(part.strip()) for part in (raw or "").split(",") if part.strip()]
    except ValueError:
        parts = []
    if len(parts) != 4:
        return defaults
    return tuple(parts)  # type: ignore[return-value]


def _format_number(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "--"
    if isinstance(value, int):
        return str(value)
    text = f"{value:.{digits}f}"
    if "." in text:
        return text.rstrip("0").rstrip(".")
    return text


def _level_index(value: float, thresholds: tuple[float, float, float, float]) -> int:
    if value >= thresholds[3]:
        return 4
    if value >= thresholds[2]:
        return 3
    if value >= thresholds[1]:
        return 2
    if value >= thresholds[0]:
        return 1
    return 0


def _band_text(index: int, thresholds: tuple[float, float, float, float], unit: str, digits: int) -> str:
    if index <= 0:
        return f"< {_format_number(thresholds[0], digits)} {unit}".strip()
    if index == 1:
        return f"{_format_number(thresholds[0], digits)} - {_format_number(thresholds[1], digits)} {unit}".strip()
    if index == 2:
        return f"{_format_number(thresholds[1], digits)} - {_format_number(thresholds[2], digits)} {unit}".strip()
    if index == 3:
        return f"{_format_number(thresholds[2], digits)} - {_format_number(thresholds[3], digits)} {unit}".strip()
    return f">= {_format_number(thresholds[3], digits)} {unit}".strip()


def _rule_text(thresholds: tuple[float, float, float, float], unit: str, digits: int) -> str:
    return "；".join(
        [
            f"关注 {_format_number(thresholds[0], digits)} - {_format_number(thresholds[1], digits)} {unit}".strip(),
            f"较严重 {_format_number(thresholds[1], digits)} - {_format_number(thresholds[2], digits)} {unit}".strip(),
            f"高等级 {_format_number(thresholds[2], digits)} - {_format_number(thresholds[3], digits)} {unit}".strip(),
            f"极高 >= {_format_number(thresholds[3], digits)} {unit}".strip(),
        ]
    )


def _normalized_score(value: float, thresholds: tuple[float, float, float, float]) -> int:
    index = _level_index(value, thresholds)
    if index == 0:
        start, end = 0.0, thresholds[0]
    elif index == 1:
        start, end = thresholds[0], thresholds[1]
    elif index == 2:
        start, end = thresholds[1], thresholds[2]
    elif index == 3:
        start, end = thresholds[2], thresholds[3]
    else:
        start = thresholds[3]
        end = thresholds[3] * 1.25 if thresholds[3] else 1.0

    span = max(end - start, 1e-9)
    offset = min(max(value - start, 0.0), span)
    return min(100, round(index * 25 + offset / span * 25))


def _base_indicator_warning(
    *,
    key: str,
    title: str,
    metric_label: str,
    basis: str,
    unit: str,
    value: float | int | None,
    thresholds: tuple[float, float, float, float],
    digits: int,
    summary: str,
    action_map: dict[str, str],
    supporting: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if value is None:
        return {
            "key": key,
            "title": title,
            "metric_label": metric_label,
            "basis": basis,
            "available": False,
            "triggered": False,
            "level": "暂无数据",
            "level_code": "unavailable",
            "severity_index": -1,
            "score": 0,
            "current_value": None,
            "display_value": "--",
            "band": "--",
            "rule_text": _rule_text(thresholds, unit, digits),
            "summary": f"{title}当前缺少有效数据，暂不判定预警等级。",
            "action": "继续补齐监测数据后再开展同口径判定。",
            "supporting": supporting or {},
            "comparison_note": settings.WARNING_HISTORY_NOTE,
            "unit": unit,
        }

    numeric_value = float(value)
    index = _level_index(numeric_value, thresholds)
    level = LEVELS[index]
    return {
        "key": key,
        "title": title,
        "metric_label": metric_label,
        "basis": basis,
        "available": True,
        "triggered": index > 0,
        "level": level["label"],
        "level_code": level["code"],
        "severity_index": index,
        "score": _normalized_score(numeric_value, thresholds),
        "current_value": numeric_value,
        "display_value": f"{_format_number(numeric_value, digits)} {unit}".strip(),
        "band": _band_text(index, thresholds, unit, digits),
        "rule_text": _rule_text(thresholds, unit, digits),
        "summary": summary,
        "action": action_map.get(level["code"]) or action_map.get("default") or "维持常规巡检。",
        "supporting": supporting or {},
        "comparison_note": settings.WARNING_HISTORY_NOTE,
        "unit": unit,
        "tone": level["tone"],
        "color": level["color"],
    }


def derive_pest_risk_level(insect_peak: int, spore_peak: int) -> str:
    insect_thresholds = _parse_thresholds(settings.WARNING_INSECT_THRESHOLDS, (40, 80, 100, 120))
    spore_thresholds = _parse_thresholds(settings.WARNING_SPORE_THRESHOLDS, (10, 30, 60, 90))
    highest = max(_level_index(float(insect_peak), insect_thresholds), _level_index(float(spore_peak), spore_thresholds))
    if highest >= 2:
        return "高"
    if highest >= 1:
        return "中"
    return "低"


def build_warning_analysis(
    *,
    recent_days: int,
    pest_management: dict[str, Any],
    runoff_erosion: dict[str, Any],
    weather_support: dict[str, Any],
) -> dict[str, Any]:
    insect_thresholds = _parse_thresholds(settings.WARNING_INSECT_THRESHOLDS, (40, 80, 100, 120))
    spore_thresholds = _parse_thresholds(settings.WARNING_SPORE_THRESHOLDS, (10, 30, 60, 90))
    rainfall_thresholds = _parse_thresholds(settings.WARNING_RAINFALL_THRESHOLDS, (10, 25, 50, 80))
    sand_thresholds = _parse_thresholds(settings.WARNING_SAND_THRESHOLDS, (0.0003, 0.0008, 0.0015, 0.003))

    insect_peak = pest_management.get("insect_peak") or {}
    spore_peak = pest_management.get("spore_peak") or {}
    top_species = pest_management.get("top_species") or {}
    weather_daily = weather_support.get("history_daily") or []
    history_summary = weather_support.get("history_summary") or {}
    highest_station = runoff_erosion.get("highest_risk_station") or {}
    reference_station = runoff_erosion.get("reference_station") or {}

    insect_warning = _base_indicator_warning(
        key="insect_peak",
        title="虫情单日峰值",
        metric_label=f"最近{recent_days}天单日虫情峰值",
        basis=f"按最近{recent_days}天日累计虫情进行分级判定",
        unit="只",
        value=insect_peak.get("count"),
        thresholds=insect_thresholds,
        digits=0,
        summary=(
            f"{insect_peak.get('date') or '--'}虫情峰值达到{_format_number(insect_peak.get('count'), 0)}只，"
            f"重点虫种为{top_species.get('name') or '未识别'}。"
        ),
        action_map={
            "normal": "维持日常巡检，持续记录虫种结构变化。",
            "attention": "建议提高巡检频次，核查优势虫种变化。",
            "severe": "建议同步开展田间复核、重点虫种排查和处置记录。",
            "high": "建议当天完成田间复核、重点虫种排查和分区处置。",
            "critical": "建议立即启动高等级病虫响应，落实处置和复核闭环。",
        },
        supporting={
            "peak_date": insect_peak.get("date"),
            "dominant_species": top_species.get("name"),
            "dominant_species_share": top_species.get("share"),
        },
    )

    spore_warning = _base_indicator_warning(
        key="spore_peak",
        title="孢子单日峰值",
        metric_label=f"最近{recent_days}天单日孢子峰值",
        basis=f"按最近{recent_days}天日累计孢子进行分级判定",
        unit="个",
        value=spore_peak.get("count"),
        thresholds=spore_thresholds,
        digits=0,
        summary=(
            f"{spore_peak.get('date') or '--'}孢子峰值为{_format_number(spore_peak.get('count'), 0)}个，"
            f"最近7个完整历史日平均湿度为{_format_number(history_summary.get('avg_humidity'), 1)}%。"
        ),
        action_map={
            "normal": "维持常规孢子监测，关注湿度波动。",
            "attention": "建议结合湿度和林下通风条件开展复核。",
            "severe": "建议加密孢子巡检，并联合湿度条件研判病害扩散风险。",
            "high": "建议立即开展病害高风险点复核与防控准备。",
            "critical": "建议启动病害应急巡检，落实高风险区快速处置。",
        },
        supporting={
            "peak_date": spore_peak.get("date"),
            "avg_humidity_7d": history_summary.get("avg_humidity"),
        },
    )

    wettest_item = max(weather_daily, key=lambda item: item.get("precip") or 0, default=None)
    rainfall_warning = _base_indicator_warning(
        key="rainfall_peak",
        title="单日降水强度",
        metric_label="最近7个完整历史日最大单日降水",
        basis="按最近7个完整自然日历史降水序列进行分级判定",
        unit="mm",
        value=wettest_item.get("precip") if wettest_item else None,
        thresholds=rainfall_thresholds,
        digits=1,
        summary=(
            f"最近7个完整历史日最大单日降水为{_format_number(wettest_item.get('precip') if wettest_item else None, 1)} mm，"
            f"对应日期为{wettest_item.get('date') if wettest_item else '--'}，7天累计降水"
            f"{_format_number(history_summary.get('total_precip'), 1)} mm。"
        ),
        action_map={
            "normal": "降水扰动较低，维持常规巡查即可。",
            "attention": "建议关注坡面汇流与积水点变化。",
            "severe": "建议加强降雨后坡面、沟道和排水口巡查。",
            "high": "建议在强降雨后立即开展坡面径流和冲刷复核。",
            "critical": "建议启动暴雨过程专项巡查，联动检查径流和侵蚀风险。",
        },
        supporting={
            "peak_date": wettest_item.get("date") if wettest_item else None,
            "seven_day_total": history_summary.get("total_precip"),
            "rainy_days": history_summary.get("rainy_days"),
        },
    )

    sand_warning = _base_indicator_warning(
        key="sand_content",
        title="含沙监测风险",
        metric_label=f"最近{recent_days}天站点平均含沙量高值",
        basis=f"按最近{recent_days}天各径流站平均含沙量高值进行分级判定",
        unit="",
        value=highest_station.get("avg_sand_content"),
        thresholds=sand_thresholds,
        digits=4,
        summary=(
            f"最近{recent_days}天含沙高值站点为{highest_station.get('name') or '--'}，"
            f"平均含沙量{_format_number(highest_station.get('avg_sand_content'), 4)}，"
            f"参照样地为{reference_station.get('name') or '--'}。"
        ),
        action_map={
            "normal": "当前含沙扰动较低，维持常规监测。",
            "attention": "建议关注裸露地表和排水路径变化。",
            "severe": "建议对高值站点开展坡面冲刷与地表覆盖复核。",
            "high": "建议立即排查高值站点上游裸露区和汇流通道。",
            "critical": "建议启动重点站点减蚀巡查和现场处置。",
        },
        supporting={
            "station_name": highest_station.get("name"),
            "erosion_proxy": highest_station.get("erosion_proxy"),
            "reference_station": reference_station.get("name"),
        },
    )

    warnings = [insect_warning, spore_warning, rainfall_warning, sand_warning]
    warnings.sort(key=lambda item: (item.get("severity_index", -1), item.get("score", 0)), reverse=True)

    active_warnings = [item for item in warnings if item.get("triggered")]
    highest = warnings[0] if warnings else None
    headline = (
        f"当前共触发 {len(active_warnings)} 项分级预警，最高为“{highest.get('title')} / {highest.get('level')}”。"
        if active_warnings and highest
        else "当前已纳入的虫情、孢子、雨量和含沙指标均未触发分级预警。"
    )

    return {
        "comparison": {
            "available": False,
            "message": settings.WARNING_HISTORY_NOTE,
        },
        "summary": {
            "has_warning": bool(active_warnings),
            "triggered_count": len(active_warnings),
            "available_count": len([item for item in warnings if item.get("available")]),
            "highest_level": highest.get("level") if highest else "暂无数据",
            "highest_level_code": highest.get("level_code") if highest else "unavailable",
            "headline": headline,
        },
        "indicator_warnings": warnings,
        "active_warnings": active_warnings,
    }
