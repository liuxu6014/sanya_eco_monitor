from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable


def _reading_value(record: Any) -> float | None:
    value = getattr(record, "daily_rainfall", None)
    if value is None:
        value = getattr(record, "rainfall", None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hourly_value(record: Any) -> float | None:
    value = getattr(record, "hourly_rainfall", None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _day_range(start_day: date, end_day: date) -> Iterable[date]:
    current = start_day
    while current <= end_day:
        yield current
        current += timedelta(days=1)


def aggregate_rainfall_daily(records: Iterable[Any], start_day: date, end_day: date) -> list[dict[str, Any]]:
    """Aggregate rain-gauge daily cumulative readings into daily rainfall.

    The upstream rain-gauge API already reports a same-day cumulative value.
    For each station/day we therefore use the latest reading of that day as the
    daily rainfall, then sum station totals for the regional rainfall.
    """

    station_daily: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "latest_reading": None,
                "latest_time": None,
                "hourly": [],
                "records": 0,
            }
        )
    )

    for record in records:
        collection_time = getattr(record, "collection_time", None)
        if not isinstance(collection_time, datetime):
            continue
        day = collection_time.date().isoformat()
        station = str(getattr(record, "device_code", "") or "unknown")
        bucket = station_daily[day][station]
        reading = _reading_value(record)
        hourly = _hourly_value(record)
        if reading is not None and (
            bucket["latest_time"] is None or collection_time >= bucket["latest_time"]
        ):
            bucket["latest_reading"] = reading
            bucket["latest_time"] = collection_time
        if hourly is not None:
            bucket["hourly"].append(hourly)
        bucket["records"] += 1

    items: list[dict[str, Any]] = []
    for day in _day_range(start_day, end_day):
        day_key = day.isoformat()
        station_values = []
        station_hourly = []
        record_count = 0
        for bucket in station_daily.get(day_key, {}).values():
            record_count += bucket["records"]
            if bucket["latest_reading"] is not None:
                station_values.append(float(bucket["latest_reading"]))
            if bucket["hourly"]:
                station_hourly.append(max(bucket["hourly"]))

        regional_rainfall = round(sum(station_values), 1) if station_values else 0
        items.append(
            {
                "date": day_key,
                "rainfall": regional_rainfall,
                "max_hourly": round(max(station_hourly), 1) if station_hourly else 0,
                "station_peak": round(max(station_values), 1) if station_values else 0,
                "station_count": len(station_values),
                "records": record_count,
            }
        )

    return items
