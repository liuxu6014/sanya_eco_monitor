import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import weather_support  # noqa: E402


class WeatherSupportResilienceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        weather_support._weather_cache["value"] = None
        weather_support._weather_cache["expires_at"] = 0.0

    def tearDown(self):
        weather_support._weather_cache["value"] = None
        weather_support._weather_cache["expires_at"] = 0.0

    async def test_weather_bundle_includes_exception_type_for_empty_httpx_errors(self):
        with patch.object(
            weather_support,
            "_fetch_history_bundle",
            AsyncMock(side_effect=httpx.ReadTimeout("")),
        ), patch.object(weather_support, "_is_forecast_enabled", return_value=False):
            result = await weather_support._fetch_weather_bundle()

        self.assertEqual("error", result["status"])
        self.assertIn("ReadTimeout", result["message"])

    async def test_weather_support_keeps_last_ok_cache_when_refresh_fails(self):
        cached = {
            "enabled": True,
            "status": "ok",
            "history_daily": [{"date": "2026-05-04"}],
            "history_summary": {"days": 1},
            "message": None,
        }
        failed = {
            "enabled": False,
            "status": "error",
            "message": "历史天气接口调用失败: ReadTimeout",
            "history_daily": [],
            "history_summary": {},
        }
        weather_support._weather_cache["value"] = cached
        weather_support._weather_cache["expires_at"] = time.monotonic() - 1

        with patch.object(
            weather_support,
            "_fetch_weather_bundle",
            AsyncMock(return_value=failed),
        ):
            result = await weather_support.get_weather_support()

        self.assertEqual("ok", result["status"])
        self.assertTrue(result["stale"])
        self.assertEqual([{"date": "2026-05-04"}], result["history_daily"])
        self.assertIn("ReadTimeout", result["message"])

    async def test_history_bundle_requests_recent_30_complete_days(self):
        captured = {}

        async def fake_get_json(_client, _url, *, params, attempts=2):
            captured.update(params)
            return {
                "daily": {
                    "time": ["2026-04-10", "2026-05-09"],
                    "temperature_2m_max": [30, 31],
                    "temperature_2m_min": [20, 21],
                    "temperature_2m_mean": [25, 26],
                    "relative_humidity_2m_mean": [80, 81],
                    "precipitation_sum": [1, 2],
                    "wind_speed_10m_max": [10, 11],
                    "wind_direction_10m_dominant": [90, 180],
                }
            }

        class FixedDateTime:
            @classmethod
            def now(cls):
                return fixed_now

            @classmethod
            def fromisoformat(cls, value):
                return fixed_now.fromisoformat(value)

        fixed_now = weather_support.datetime
        FixedDateTime.now = classmethod(lambda cls: fixed_now(2026, 5, 10, 12, 0, 0))
        FixedDateTime.fromisoformat = classmethod(lambda cls, value: fixed_now.fromisoformat(value))

        with patch.object(weather_support.settings, "QWEATHER_LOCATION", "109.5,18.2"), patch.object(
            weather_support,
            "_get_json_with_retries",
            side_effect=fake_get_json,
        ), patch.object(weather_support, "datetime", FixedDateTime):
            result = await weather_support._fetch_history_bundle()

        self.assertEqual("2026-04-10", captured["start_date"])
        self.assertEqual("2026-05-09", captured["end_date"])
        self.assertEqual(2, result["summary"]["days"])


if __name__ == "__main__":
    unittest.main()
