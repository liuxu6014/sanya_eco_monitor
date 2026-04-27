from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import httpx

from config import settings


logger = logging.getLogger(__name__)

_weather_cache: dict[str, object] = {
    "value": None,
    "expires_at": 0.0,
}
_weather_lock = asyncio.Lock()


def _to_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _average(values: list[float | None], digits: int = 1) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), digits)


def _series_value(series: Any, index: int) -> float | None:
    if not isinstance(series, list) or index >= len(series):
        return None
    return _to_float(series[index])


def _wind_direction_text(degrees: float | None) -> str | None:
    if degrees is None:
        return None
    labels = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    index = int(((degrees % 360) + 22.5) // 45) % len(labels)
    return labels[index]


def _dominant_wind_direction(degrees_list: list[float | None]) -> tuple[float | None, str | None]:
    sectors = [_wind_direction_text(value) for value in degrees_list if value is not None]
    if not sectors:
        return None, None
    sector, _ = Counter(sectors).most_common(1)[0]
    degree_map = {
        "北": 0.0,
        "东北": 45.0,
        "东": 90.0,
        "东南": 135.0,
        "南": 180.0,
        "西南": 225.0,
        "西": 270.0,
        "西北": 315.0,
    }
    return degree_map.get(sector), sector


def _estimate_hargreaves_et0(
    *,
    date_value: str | None,
    latitude: float | None,
    temp_min: float | None,
    temp_max: float | None,
    temp_mean: float | None,
) -> float | None:
    if not date_value or latitude is None or temp_min is None or temp_max is None or temp_mean is None:
        return None

    temp_delta = max(temp_max - temp_min, 0.0)
    if temp_delta == 0:
        return 0.0

    try:
        day_of_year = datetime.fromisoformat(date_value).timetuple().tm_yday
    except ValueError:
        return None

    latitude_rad = math.radians(latitude)
    inverse_distance = 1 + 0.033 * math.cos((2 * math.pi / 365) * day_of_year)
    solar_declination = 0.409 * math.sin((2 * math.pi / 365) * day_of_year - 1.39)
    sunset_term = -math.tan(latitude_rad) * math.tan(solar_declination)
    sunset_term = min(1.0, max(-1.0, sunset_term))
    sunset_hour_angle = math.acos(sunset_term)

    extraterrestrial_radiation = (
        (24 * 60 / math.pi)
        * 0.0820
        * inverse_distance
        * (
            sunset_hour_angle * math.sin(latitude_rad) * math.sin(solar_declination)
            + math.cos(latitude_rad) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
        )
    )
    et0 = 0.0023 * (temp_mean + 17.8) * math.sqrt(temp_delta) * extraterrestrial_radiation
    return round(max(et0, 0.0), 2)


def _is_forecast_enabled() -> bool:
    return bool(
        settings.QWEATHER_ENABLED
        and settings.QWEATHER_API_KEY.strip()
        and settings.QWEATHER_API_HOST.strip()
        and settings.QWEATHER_LOCATION.strip()
    )


def _parse_location() -> tuple[float, float] | None:
    raw = settings.QWEATHER_LOCATION.strip()
    if not raw or "," not in raw:
        return None
    lon_str, lat_str = [part.strip() for part in raw.split(",", 1)]
    lon = _to_float(lon_str)
    lat = _to_float(lat_str)
    if lon is None or lat is None:
        return None
    return lon, lat


def _base_url() -> str:
    host = settings.QWEATHER_API_HOST.strip().rstrip("/")
    if host.startswith(("http://", "https://")):
        return host
    return f"https://{host}"


def _empty_forecast_result(message: str, status: str = "disabled") -> dict[str, Any]:
    return {
        "enabled": False,
        "status": status,
        "source": "QWeather",
        "message": message,
        "updated_at": None,
        "current": {},
        "daily": [],
        "summary": {},
    }


def _empty_history_result(message: str, status: str = "disabled") -> dict[str, Any]:
    return {
        "enabled": False,
        "status": status,
        "source": "Open-Meteo Archive",
        "message": message,
        "updated_at": None,
        "daily": [],
        "summary": {},
        "range": {},
    }


def _summarize_history(items: list[dict[str, Any]]) -> dict[str, Any]:
    rainy_items = [item for item in items if (item.get("precip") or 0) > 0]
    wettest_item = max(items, key=lambda item: item.get("precip") or 0, default=None)
    windiest_item = max(items, key=lambda item: item.get("wind_speed_max") or 0, default=None)

    dominant_wind_direction, dominant_wind_direction_text = _dominant_wind_direction(
        [item.get("wind_direction") for item in items]
    )

    temp_ranges = [
        round((item["temp_max"] - item["temp_min"]), 1)
        for item in items
        if item.get("temp_max") is not None and item.get("temp_min") is not None
    ]

    return {
        "days": len(items),
        "avg_temp_max": _average([item.get("temp_max") for item in items]),
        "avg_temp_min": _average([item.get("temp_min") for item in items]),
        "avg_temp_mean": _average([item.get("temp_mean") for item in items]),
        "avg_temp_range": _average(temp_ranges),
        "avg_humidity": _average([item.get("humidity_mean") for item in items]),
        "total_precip": round(sum(item.get("precip") or 0 for item in items), 2),
        "rainy_days": len(rainy_items),
        "max_precip": wettest_item.get("precip") if wettest_item else None,
        "wettest_day": wettest_item.get("date") if wettest_item and (wettest_item.get("precip") or 0) > 0 else None,
        "avg_wind_speed": _average([item.get("wind_speed_max") for item in items]),
        "max_wind_speed": windiest_item.get("wind_speed_max") if windiest_item else None,
        "windiest_day": windiest_item.get("date") if windiest_item and windiest_item.get("wind_speed_max") is not None else None,
        "dominant_wind_direction": dominant_wind_direction,
        "dominant_wind_direction_text": dominant_wind_direction_text,
        "avg_et0_estimate": _average([item.get("et0_estimate") for item in items], digits=2),
        "total_et0_estimate": round(sum(item.get("et0_estimate") or 0 for item in items), 2),
    }


async def _fetch_forecast_bundle() -> dict[str, Any]:
    if not _is_forecast_enabled():
        return _empty_forecast_result("未配置和风天气参数，无法获取实时与预报天气。")

    params = {
        "key": settings.QWEATHER_API_KEY,
        "location": settings.QWEATHER_LOCATION,
        "lang": settings.QWEATHER_LANG,
        "unit": settings.QWEATHER_UNIT,
    }
    timeout = httpx.Timeout(12.0, connect=6.0)
    base_url = _base_url()

    async with httpx.AsyncClient(timeout=timeout) as client:
        now_req = client.get(f"{base_url}/v7/weather/now", params=params)
        daily_req = client.get(f"{base_url}/v7/weather/7d", params=params)
        now_resp, daily_resp = await asyncio.gather(now_req, daily_req)
        now_resp.raise_for_status()
        daily_resp.raise_for_status()

    now_json = now_resp.json()
    daily_json = daily_resp.json()
    now = now_json.get("now") or {}
    daily = daily_json.get("daily") or []

    daily_items = [
        {
            "date": item.get("fxDate"),
            "text_day": item.get("textDay"),
            "text_night": item.get("textNight"),
            "temp_max": _to_float(item.get("tempMax")),
            "temp_min": _to_float(item.get("tempMin")),
            "humidity": _to_float(item.get("humidity")),
            "precip": _to_float(item.get("precip")),
            "pressure": _to_float(item.get("pressure")),
            "wind_speed_day": _to_float(item.get("windSpeedDay")),
        }
        for item in daily
    ]

    return {
        "enabled": True,
        "status": "ok",
        "source": "QWeather",
        "updated_at": now_json.get("updateTime") or daily_json.get("updateTime"),
        "current": {
            "text": now.get("text"),
            "temp": _to_float(now.get("temp")),
            "feels_like": _to_float(now.get("feelsLike")),
            "humidity": _to_float(now.get("humidity")),
            "wind_speed": _to_float(now.get("windSpeed")),
            "pressure": _to_float(now.get("pressure")),
            "precip": _to_float(now.get("precip")),
            "obs_time": now.get("obsTime"),
        },
        "daily": daily_items,
        "summary": {
            "days": len(daily_items),
            "avg_temp_max": _average([item.get("temp_max") for item in daily_items]),
            "avg_temp_min": _average([item.get("temp_min") for item in daily_items]),
            "avg_humidity": _average([item.get("humidity") for item in daily_items]),
            "avg_wind_speed": _average([item.get("wind_speed_day") for item in daily_items]),
            "total_precip": round(sum(item.get("precip") or 0 for item in daily_items), 2),
        },
    }


async def _fetch_history_bundle() -> dict[str, Any]:
    location = _parse_location()
    if location is None:
        return _empty_history_result("未配置天气坐标，无法获取最近7天历史天气。")

    lon, lat = location
    end_date = datetime.now().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    timeout = httpx.Timeout(12.0, connect=6.0)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "relative_humidity_2m_mean",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant",
            ]
        ),
        "timezone": "Asia/Shanghai",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get("https://archive-api.open-meteo.com/v1/archive", params=params)
        resp.raise_for_status()

    payload = resp.json()
    daily = payload.get("daily") or {}
    days = daily.get("time") or []

    items: list[dict[str, Any]] = []
    for index, day in enumerate(days):
        temp_max = _series_value(daily.get("temperature_2m_max"), index)
        temp_min = _series_value(daily.get("temperature_2m_min"), index)
        temp_mean = _series_value(daily.get("temperature_2m_mean"), index)
        wind_direction = _series_value(daily.get("wind_direction_10m_dominant"), index)
        item = {
            "date": day,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "temp_mean": temp_mean,
            "temp_range": round((temp_max - temp_min), 1) if temp_max is not None and temp_min is not None else None,
            "humidity_mean": _series_value(daily.get("relative_humidity_2m_mean"), index),
            "precip": _series_value(daily.get("precipitation_sum"), index),
            "wind_speed_max": _series_value(daily.get("wind_speed_10m_max"), index),
            "wind_direction": wind_direction,
            "wind_direction_text": _wind_direction_text(wind_direction),
            "et0_estimate": _estimate_hargreaves_et0(
                date_value=day,
                latitude=lat,
                temp_min=temp_min,
                temp_max=temp_max,
                temp_mean=temp_mean,
            ),
        }
        items.append(item)

    if not items:
        return _empty_history_result("历史天气接口未返回有效数据。", status="error")

    return {
        "enabled": True,
        "status": "ok",
        "source": "Open-Meteo Archive",
        "updated_at": datetime.now().isoformat(),
        "daily": items,
        "summary": _summarize_history(items),
        "range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    }


async def _fetch_weather_bundle() -> dict[str, Any]:
    forecast = _empty_forecast_result("未配置和风天气参数，无法获取实时与预报天气。")
    history = _empty_history_result("未配置天气坐标，无法获取最近7天历史天气。")

    tasks: list[tuple[str, Any]] = [("history", _fetch_history_bundle())]
    if _is_forecast_enabled():
        tasks.append(("forecast", _fetch_forecast_bundle()))

    results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)

    for (name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch %s weather data: %s", name, result)
            if name == "history":
                history = _empty_history_result(f"历史天气接口调用失败: {result}", status="error")
            else:
                forecast = _empty_forecast_result(f"气象接口调用失败: {result}", status="error")
            continue

        if name == "history":
            history = result
        else:
            forecast = result

    forecast_ok = forecast.get("status") == "ok"
    history_ok = history.get("status") == "ok"
    enabled = forecast_ok or history_ok

    if not enabled:
        return {
            "enabled": False,
            "status": "error"
            if forecast.get("status") == "error" or history.get("status") == "error"
            else "disabled",
            "source": "Weather API",
            "location": settings.QWEATHER_LOCATION,
            "message": history.get("message") or forecast.get("message"),
            "updated_at": None,
            "current": {},
            "daily": [],
            "summary": {},
            "history_daily": [],
            "history_summary": {},
            "history_range": {},
        }

    sources = [
        source
        for source in [history.get("source") if history_ok else None, forecast.get("source") if forecast_ok else None]
        if source
    ]

    return {
        "enabled": True,
        "status": "ok",
        "source": " + ".join(sources) if sources else "Weather API",
        "location": settings.QWEATHER_LOCATION,
        "message": history.get("message") or forecast.get("message"),
        "updated_at": forecast.get("updated_at") or history.get("updated_at"),
        "current": forecast.get("current") or {},
        "daily": forecast.get("daily") or [],
        "summary": forecast.get("summary") or {},
        "history_daily": history.get("daily") or [],
        "history_summary": history.get("summary") or {},
        "history_range": history.get("range") or {},
        "history_source": history.get("source"),
        "forecast_source": forecast.get("source"),
    }


async def get_weather_support(*, force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        async with _weather_lock:
            data = await _fetch_weather_bundle()
            _weather_cache["value"] = data
            _weather_cache["expires_at"] = time.monotonic() + max(60, settings.QWEATHER_CACHE_SECONDS)
            return data

    now = time.monotonic()
    cached_value = _weather_cache["value"]
    expires_at = float(_weather_cache["expires_at"])
    if isinstance(cached_value, dict) and now < expires_at:
        return cached_value

    async with _weather_lock:
        now = time.monotonic()
        cached_value = _weather_cache["value"]
        expires_at = float(_weather_cache["expires_at"])
        if isinstance(cached_value, dict) and now < expires_at:
            return cached_value

        data = await _fetch_weather_bundle()
        _weather_cache["value"] = data
        _weather_cache["expires_at"] = now + max(60, settings.QWEATHER_CACHE_SECONDS)
        return data
