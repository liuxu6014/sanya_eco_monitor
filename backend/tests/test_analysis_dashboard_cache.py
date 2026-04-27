import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import analysis_dashboard  # noqa: E402


class AnalysisDashboardCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        analysis_dashboard._dashboard_cache["value"] = None
        analysis_dashboard._dashboard_cache["expires_at"] = 0.0

    async def test_dashboard_bundle_uses_cache_within_ttl(self):
        payload = {"eco_index": {"eco_health": 92}}

        with patch.object(
            analysis_dashboard,
            "_fetch_dashboard_bundle",
            AsyncMock(return_value=payload),
        ) as fetch_mock:
            first = await analysis_dashboard.get_dashboard_bundle(db=None, ttl_seconds=60)
            second = await analysis_dashboard.get_dashboard_bundle(db=None, ttl_seconds=60)

        self.assertEqual(payload, first)
        self.assertEqual(payload, second)
        self.assertEqual(1, fetch_mock.await_count)

    async def test_dashboard_bundle_force_refresh_bypasses_cache(self):
        with patch.object(
            analysis_dashboard,
            "_fetch_dashboard_bundle",
            AsyncMock(side_effect=[{"version": 1}, {"version": 2}]),
        ) as fetch_mock:
            first = await analysis_dashboard.get_dashboard_bundle(db=None, ttl_seconds=60)
            second = await analysis_dashboard.get_dashboard_bundle(
                db=None,
                ttl_seconds=60,
                force_refresh=True,
            )

        self.assertEqual({"version": 1}, first)
        self.assertEqual({"version": 2}, second)
        self.assertEqual(2, fetch_mock.await_count)


if __name__ == "__main__":
    unittest.main()
