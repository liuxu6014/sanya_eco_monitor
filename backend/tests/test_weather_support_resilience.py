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


if __name__ == "__main__":
    unittest.main()
