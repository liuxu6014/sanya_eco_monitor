import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers import analysis as analysis_router  # noqa: E402
from services import analysis_dashboard  # noqa: E402
from models import RunoffRecord  # noqa: E402


class AnalysisRuntimeCacheRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        analysis_router._analysis_runtime_cache["value"].clear()
        analysis_router._analysis_runtime_cache["expires_at"].clear()

    async def test_eco_index_route_uses_runtime_cache_within_ttl(self):
        with patch.object(analysis_router.settings, "ANALYSIS_RUNTIME_CACHE_SECONDS", 60):
            with patch("routers.analysis.build_eco_index_payload", new=AsyncMock(return_value={"eco_health": 88})) as build_mock:
                first = await analysis_router.get_eco_index(db="db-a")
                second = await analysis_router.get_eco_index(db="db-b")

        self.assertEqual({"data": {"eco_health": 88}}, first)
        self.assertEqual(first, second)
        self.assertEqual(1, build_mock.await_count)


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


class AnalysisDashboardRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_route_passes_force_refresh_query_flag(self):
        with patch("routers.analysis.get_dashboard_bundle", new=AsyncMock(return_value={"ok": True})) as fetch_mock:
            response = await analysis_router.get_analysis_dashboard(force_refresh=True, db=None)

        self.assertEqual({"data": {"ok": True}}, response)
        self.assertEqual(1, fetch_mock.await_count)
        _, kwargs = fetch_mock.await_args
        self.assertTrue(kwargs["force_refresh"])


class AnalysisEcoIndexTests(unittest.IsolatedAsyncioTestCase):
    async def test_eco_index_filters_out_of_range_hydrology_values(self):
        now = datetime(2026, 5, 20, 12, 0, 0)
        runoff_records = [
            RunoffRecord(
                device_code="a",
                collection_time=now - timedelta(hours=1),
                flow_rate=327.67,
                sand_content=32.767,
                runoff=786.408,
                water_level=327.67,
            ),
            RunoffRecord(
                device_code="b",
                collection_time=now - timedelta(minutes=30),
                flow_rate=1.25,
                sand_content=0.013,
                runoff=0.25,
                water_level=0.42,
            ),
        ]

        class _ScalarResult:
            def __init__(self, records):
                self._records = records

            def all(self):
                return self._records

        class _ExecuteResult:
            def __init__(self, records):
                self._records = records

            def scalars(self):
                return _ScalarResult(self._records)

        class _Db:
            async def execute(self, query):
                text = str(query)
                if "FROM runoff_records" in text:
                    return _ExecuteResult(runoff_records)
                return _ExecuteResult([])

        with patch.object(analysis_dashboard, "resolve_water_quality_codes", new=AsyncMock(return_value=[])):
            with patch.object(analysis_dashboard, "get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                with patch.object(analysis_dashboard, "datetime") as datetime_mock:
                    datetime_mock.now.return_value = now
                    datetime_mock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                    payload = await analysis_dashboard.build_eco_index_payload(_Db())

        self.assertEqual(1.25, payload["meta"]["avg_flow_rate_24h"])
        self.assertEqual(0.25, payload["meta"]["avg_runoff_24h"])
        self.assertEqual(0.01, payload["meta"]["avg_sand_content_24h"])
        self.assertEqual(0.42, payload["meta"]["avg_water_level_24h"])


if __name__ == "__main__":
    unittest.main()
