from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _to_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric


def flag_numeric_anomalies(
    record: Mapping[str, Any],
    rules: Mapping[str, Mapping[str, Any]],
    *,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    context = context or {}
    for metric, rule in rules.items():
        numeric = _to_number(record.get(metric))
        if numeric is None:
            continue

        minimum = rule.get("min")
        maximum = rule.get("max")
        triggered = False
        reason = ""
        if minimum is not None and numeric < float(minimum):
            triggered = True
            reason = f"< {minimum}"
        elif maximum is not None and numeric > float(maximum):
            triggered = True
            reason = f"> {maximum}"

        if not triggered:
            continue

        flags.append(
            {
                "metric": metric,
                "label": rule.get("label") or metric,
                "value": numeric,
                "reason": reason,
                **context,
            }
        )
    return flags


def build_anomaly_summary(
    flags: list[dict[str, Any]],
    *,
    subject: str,
) -> dict[str, Any]:
    metrics = []
    for item in flags:
        metric = item.get("metric")
        if metric and metric not in metrics:
            metrics.append(metric)

    has_anomaly = bool(flags)
    return {
        "has_anomaly": has_anomaly,
        "count": len(flags),
        "metrics": metrics,
        "message": (
            f"{subject}已检测到 {len(flags)} 处异常值，当前返回的是设备原始值，未做过滤。"
            if has_anomaly
            else f"{subject}未检测到异常值。"
        ),
    }
