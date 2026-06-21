import inspect
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import SporeRecord  # noqa: E402
from routers import summary  # noqa: E402


class _FakeScalarResult:
    def __init__(self, records):
        self._records = records

    def all(self):
        return self._records


class _FakeExecuteResult:
    def __init__(self, records):
        self._records = records

    def scalars(self):
        return _FakeScalarResult(self._records)

    def scalar_one_or_none(self):
        return self._records[0] if self._records else None


class _FakeDb:
    def __init__(self, spore_records):
        self._spore_records = spore_records

    async def execute(self, query):
        text = str(query)
        if "FROM spore_records" in text:
            return _FakeExecuteResult(self._spore_records)
        return _FakeExecuteResult([])


class SummaryDeviceStatusTests(unittest.TestCase):
    def test_core_device_status_entries_use_configured_device_codes(self):
        source = inspect.getsource(summary.get_device_status)

        self.assertIn('"code": settings.INSECT_CODE', source)
        self.assertIn('"code": settings.SPORE_CODE', source)
        self.assertIn('"code": configured_water_code', source)
        self.assertNotIn('"code": "insect"', source)
        self.assertNotIn('"code": "spore"', source)
        self.assertNotIn('"code": "water"', source)

    def test_device_status_avoids_per_device_last_time_queries(self):
        source = inspect.getsource(summary.get_device_status)
        self.assertNotIn("async def last_time", source)
        self.assertNotIn("await last_time(", source)

    def test_device_status_probe_uses_configurable_tls_verification(self):
        source = inspect.getsource(summary._probe_device_statuses)
        self.assertIn("verify=settings.HTTP_TLS_VERIFY", source)
        self.assertNotIn("AsyncClient(verify=False", source)

    def test_water_rain_and_runoff_devices_use_stale_timeout_policy(self):
        source = inspect.getsource(summary.get_device_status)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["water"]', source)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["rain"]', source)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["runoff"]', source)
        self.assertNotIn('DEVICE_STATUS_STALE_THRESHOLDS["insect"]', source)
        self.assertNotIn('DEVICE_STATUS_STALE_THRESHOLDS["spore"]', source)

    def test_insect_and_spore_keep_direct_probe_status_mapping(self):
        source = inspect.getsource(summary.get_device_status)
        self.assertIn('"status": device_statuses.get("insect", "offline")', source)
        self.assertIn('"status": device_statuses.get("spore", "offline")', source)
        self.assertNotIn('"status": device_statuses.get(f"rain_{code}", "offline")', source)
        self.assertNotIn('"status": device_statuses.get(f"runoff_{code}", "offline")', source)

    def test_overview_water_rain_and_runoff_devices_use_same_stale_timeout_policy(self):
        source = inspect.getsource(summary._build_overview_payload)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["water"]', source)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["rain"]', source)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["runoff"]', source)
        self.assertIn('"status": _resolve_device_health_status(', source)

    def test_overview_runoff_rainfall_uses_rain_gauge_daily_totals(self):
        source = inspect.getsource(summary._build_overview_payload)
        self.assertIn('runoff_rain_mapping = _build_runoff_rain_mapping(device_meta)', source)
        self.assertIn('mapped_rain_code = runoff_rain_mapping.get(code)', source)
        self.assertIn('today_rainfall_by_code.get(mapped_rain_code)', source)
        self.assertIn('today_rainfall = None', source)
        self.assertIn('elif record.rainfall is not None and record.collection_time >= today:', source)
        self.assertIn('latest_ten_rain_records = await _get_latest_n_records_by_codes(db, RainfallRecord, rain_codes, limit=10)', source)
        self.assertIn('"realtime_rainfall": realtime_rainfall_by_code.get(code)', source)

    def test_calculate_realtime_rainfall_uses_latest_minus_tenth_record(self):
        latest = type("RainLike", (), {"rainfall": 113.0})()
        records = [latest]
        for value in [110.0, 108.0, 107.0, 105.0, 103.0, 101.0, 99.0, 95.0]:
            records.append(type("RainLike", (), {"rainfall": value})())
        tenth = type("RainLike", (), {"rainfall": 90.0})()
        records.append(tenth)

        self.assertEqual(23.0, summary._calculate_realtime_rainfall(records))

    def test_calculate_realtime_rainfall_returns_none_when_tenth_record_missing(self):
        latest = type("RainLike", (), {"rainfall": 113.0})()

        self.assertIsNone(summary._calculate_realtime_rainfall([latest]))

    def test_calculate_realtime_rainfall_clamps_negative_difference_to_zero(self):
        latest = type("RainLike", (), {"rainfall": 2.0})()
        records = [latest]
        for value in [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0]:
            records.append(type("RainLike", (), {"rainfall": value})())
        tenth = type("RainLike", (), {"rainfall": 30.0})()
        records.append(tenth)

        self.assertEqual(0, summary._calculate_realtime_rainfall(records))

    def test_resolve_device_health_marks_probe_success_with_fresh_data_as_online(self):
        now = datetime(2026, 5, 14, 10, 0, 0)
        status = summary._resolve_device_health_status(
            probed_status="online",
            last_data_time=now - timedelta(minutes=20),
            stale_after=timedelta(minutes=90),
            now=now,
        )
        self.assertEqual("online", status)

    def test_resolve_device_health_marks_probe_success_with_stale_data_as_timeout(self):
        now = datetime(2026, 5, 14, 10, 0, 0)
        status = summary._resolve_device_health_status(
            probed_status="online",
            last_data_time=now - timedelta(hours=3),
            stale_after=timedelta(minutes=90),
            now=now,
        )
        self.assertEqual("timeout", status)

    def test_resolve_device_health_marks_probe_success_without_data_as_timeout(self):
        now = datetime(2026, 5, 14, 10, 0, 0)
        status = summary._resolve_device_health_status(
            probed_status="online",
            last_data_time=None,
            stale_after=timedelta(minutes=90),
            now=now,
        )
        self.assertEqual("timeout", status)

    def test_resolve_device_health_keeps_probe_failure_as_offline(self):
        now = datetime(2026, 5, 14, 10, 0, 0)
        status = summary._resolve_device_health_status(
            probed_status="offline",
            last_data_time=now - timedelta(minutes=5),
            stale_after=timedelta(minutes=90),
            now=now,
        )
        self.assertEqual("offline", status)


class SummaryDeviceStatusCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        summary._device_status_cache["value"] = None
        summary._device_status_cache["expires_at"] = 0.0
        summary._device_status_cache["refresh_task"] = None

    async def test_returns_stale_status_while_refresh_runs_in_background(self):
        summary._device_status_cache["value"] = {"insect": "online"}
        summary._device_status_cache["expires_at"] = 0.0

        created_tasks = []

        class _FakeTask:
            def add_done_callback(self, callback):
                self.callback = callback

        with patch("routers.summary._probe_device_statuses", new=AsyncMock(return_value={"insect": "offline"})) as probe_mock:
            with patch("routers.summary.asyncio.create_task", side_effect=lambda coro: created_tasks.append(coro) or _FakeTask()) as create_task_mock:
                result = await summary._get_device_statuses()

        self.assertEqual({"insect": "online"}, result)
        self.assertEqual(1, create_task_mock.call_count)
        probe_mock.assert_not_awaited()

        for coro in created_tasks:
            coro.close()

    async def test_without_cached_status_waits_for_probe_once(self):
        with patch("routers.summary._probe_device_statuses", new=AsyncMock(return_value={"water": "online"})) as probe_mock:
            result = await summary._get_device_statuses()

        self.assertEqual({"water": "online"}, result)
        probe_mock.assert_awaited_once()


class SummaryDeviceStatusBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_device_status_marks_stale_rain_and_runoff_devices_as_timeout(self):
        now = datetime(2026, 5, 20, 12, 0, 0)

        class _StatusDb:
            async def execute(self, _query):
                return _FakeExecuteResult([None])

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={
            "insect": "online",
            "spore": "online",
            "water": "online",
            "rain_16132920": "online",
            "runoff_16132920": "online",
        })):
            with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                    with patch("routers.summary._get_latest_collection_times_by_codes", new=AsyncMock(side_effect=[
                        {"16132920": now - timedelta(hours=3)},
                        {"16132920": now - timedelta(hours=3)},
                    ])):
                        with patch("routers.summary.datetime") as datetime_mock:
                            datetime_mock.now.return_value = now
                            datetime_mock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                            response = await summary.get_device_status(db=_StatusDb())

        rain = next(item for item in response["data"] if item["code"] == "16132920" and "4G" in item["name"])
        runoff = next(item for item in response["data"] if item["code"] == "16132920" and "4G" not in item["name"])
        self.assertEqual("timeout", rain["status"])
        self.assertEqual("timeout", runoff["status"])


class SummaryOverviewCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        summary._overview_cache["value"] = None
        summary._overview_cache["expires_at"] = 0.0
        summary._overview_cache["refresh_task"] = None

    async def test_overview_returns_stale_payload_while_background_refresh_is_scheduled(self):
        summary._overview_cache["value"] = {"data": {"insect": {"latest_count": 7}}}
        summary._overview_cache["expires_at"] = 0.0

        created_tasks = []

        class _FakeTask:
            def add_done_callback(self, callback):
                self.callback = callback

            def done(self):
                return False

        with patch("routers.summary._build_overview_payload", new=AsyncMock(return_value={"data": {"insect": {"latest_count": 9}}})) as build_mock:
            with patch("routers.summary.asyncio.create_task", side_effect=lambda coro: created_tasks.append(coro) or _FakeTask()) as create_task_mock:
                result = await summary._get_cached_overview_payload(db=None)

        self.assertEqual({"data": {"insect": {"latest_count": 7}}}, result)
        self.assertEqual(1, create_task_mock.call_count)
        build_mock.assert_not_awaited()

        for coro in created_tasks:
            coro.close()

    async def test_overview_without_cache_builds_payload_immediately(self):
        with patch("routers.summary._build_overview_payload", new=AsyncMock(return_value={"data": {"weather_support": {"status": "ok"}}})) as build_mock:
            result = await summary._get_cached_overview_payload(db="fake-db")

        self.assertEqual({"data": {"weather_support": {"status": "ok"}}}, result)
        build_mock.assert_awaited_once_with("fake-db")


class SummaryOverviewSporeImageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        summary._overview_cache["value"] = None
        summary._overview_cache["expires_at"] = 0.0
        summary._overview_cache["refresh_task"] = None

    async def test_overview_filters_black_spore_image_and_falls_back(self):
        now = datetime(2026, 5, 13, 10, 0, 0)
        spore_records = [
            SporeRecord(
                id=1,
                device_code="spore-1",
                collection_time=now,
                total_count=5,
                spore_data={"孢子": 5},
                image_url="https://example.com/black.jpg",
            ),
            SporeRecord(
                id=2,
                device_code="spore-1",
                collection_time=now - timedelta(hours=1),
                total_count=4,
                spore_data={"孢子": 4},
                image_url="https://example.com/normal.jpg",
            ),
        ]

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        with patch("routers.summary.aggregate_rainfall_daily", return_value=[]):
                            with patch("routers.summary.is_probably_black_image", new=AsyncMock(side_effect=[True, False])):
                                response = await summary.get_overview(db=_FakeDb(spore_records))

        payload = response["data"]
        self.assertEqual("https://example.com/normal.jpg", payload["spore"]["image_url"])

    async def test_overview_does_not_use_per_device_latest_queries_for_runoff_and_rain(self):
        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        with patch("routers.summary._get_latest_by_code", new=AsyncMock(side_effect=AssertionError("should not be called"))):
                            with patch("routers.summary._get_latest_non_null_field_by_code", new=AsyncMock(side_effect=AssertionError("should not be called"))):
                                with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                    with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                        await summary.get_overview(db=_FakeDb([]))

    async def test_overview_uses_stale_timeout_policy_for_rain_status(self):
        source = inspect.getsource(summary._build_overview_payload)
        self.assertIn('DEVICE_STATUS_STALE_THRESHOLDS["rain"]', source)
        self.assertIn('"status": _resolve_device_health_status(', source)

    async def test_overview_includes_device_meta_payload(self):
        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                            with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                response = await summary.get_overview(db=_FakeDb([]))

        payload = response["data"]
        self.assertIn("device_meta", payload)
        self.assertIn("runoff_devices", payload["device_meta"])
        self.assertIn("rain_gauges", payload["device_meta"])
        self.assertIn("water_quality", payload["device_meta"])
        self.assertIn("insect", payload["device_meta"])
        self.assertIn("spore", payload["device_meta"])

    async def test_overview_keeps_configured_rain_gauges_with_zero_daily_rainfall_when_latest_record_missing(self):
        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        async def fake_latest_records(_db, model, codes):
                            return {code: None for code in codes}

                        with patch("routers.summary._get_latest_records_by_codes", new=AsyncMock(side_effect=fake_latest_records)):
                            with patch("routers.summary._get_records_since_by_codes", new=AsyncMock(return_value={code: [] for code in ["16132920", "16132921", "16132922"]})):
                                with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                    with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                        response = await summary.get_overview(db=_FakeDb([]))

        rain_gauges = response["data"]["rain_gauges"]
        self.assertIn("16132920", rain_gauges)
        self.assertEqual(0, rain_gauges["16132920"]["rainfall"])
        self.assertIsNone(rain_gauges["16132920"]["updated_at"])

    async def test_overview_maps_runoff_rainfall_only_for_matching_rain_gauge_codes(self):
        now = datetime(2026, 5, 20, 23, 1, 40)

        class _OverviewDb:
            async def execute(self, query):
                text = str(query)
                if "FROM insect_records" in text or "FROM spore_records" in text or "FROM collect_logs" in text:
                    return _FakeExecuteResult([])
                if "max(insect_records.collection_time)" in text or "max(spore_records.collection_time)" in text:
                    return _FakeExecuteResult([None])
                return _FakeExecuteResult([])

        runoff_record = type("RunoffLike", (), {
            "device_code": "16132920",
            "collection_time": now,
            "flow_speed": 0.0,
            "flow_rate": 1.23,
            "total_flow": 0.0,
            "water_level": 0.0,
            "sand_content": 0.0,
            "liquid_pressure": 0.56,
            "runoff": 0.0,
            "rainfall": 999.0,
        })()
        rain_record = type("RainLike", (), {
            "device_code": "16132920",
            "collection_time": now,
            "rainfall": 113.0,
        })()

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={"runoff_16132920": "online", "rain_16132920": "online"})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        async def fake_latest_records(_db, model, codes):
                            if model.__name__ == "RunoffRecord":
                                return {code: (runoff_record if code == "16132920" else None) for code in codes}
                            return {code: (rain_record if code == "16132920" else None) for code in codes}

                        with patch("routers.summary._get_latest_records_by_codes", new=AsyncMock(side_effect=fake_latest_records)):
                            with patch("routers.summary._get_latest_non_null_fields_by_codes", new=AsyncMock(return_value={})):
                                with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                    with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                        with patch("routers.summary.datetime") as datetime_mock:
                                            datetime_mock.now.return_value = now
                                            datetime_mock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                                            response = await summary.get_overview(db=_OverviewDb())

        station = response["data"]["runoff_stations"]["16132920"]
        self.assertEqual(113.0, station["rainfall"])
        self.assertEqual("16132920", station["rainfall_source_code"])

    async def test_overview_clears_today_rainfall_when_latest_rain_record_is_from_yesterday(self):
        now = datetime(2026, 5, 20, 9, 0, 0)
        yesterday = now - timedelta(hours=10)

        class _OverviewDb:
            async def execute(self, query):
                text = str(query)
                if "FROM insect_records" in text or "FROM spore_records" in text or "FROM collect_logs" in text:
                    return _FakeExecuteResult([])
                if "max(insect_records.collection_time)" in text or "max(spore_records.collection_time)" in text:
                    return _FakeExecuteResult([None])
                return _FakeExecuteResult([])

        runoff_record = type("RunoffLike", (), {
            "device_code": "16132920",
            "collection_time": now,
            "flow_speed": 0.0,
            "flow_rate": 1.23,
            "total_flow": 0.0,
            "water_level": 0.0,
            "sand_content": 0.0,
            "liquid_pressure": 0.56,
            "runoff": 0.0,
            "rainfall": 999.0,
        })()
        stale_rain_record = type("RainLike", (), {
            "device_code": "16132920",
            "collection_time": yesterday,
            "rainfall": 113.0,
        })()

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={"runoff_16132920": "online", "rain_16132920": "online"})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        async def fake_latest_records(_db, model, codes):
                            if model.__name__ == "RunoffRecord":
                                return {code: (runoff_record if code == "16132920" else None) for code in codes}
                            return {code: (stale_rain_record if code == "16132920" else None) for code in codes}

                        with patch("routers.summary._get_latest_records_by_codes", new=AsyncMock(side_effect=fake_latest_records)):
                            with patch("routers.summary._get_latest_n_records_by_codes", new=AsyncMock(return_value={"16132920": [stale_rain_record], "16132921": [], "16132922": []})):
                                with patch("routers.summary._get_latest_non_null_fields_by_codes", new=AsyncMock(return_value={})):
                                    with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                        with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                            with patch("routers.summary.datetime") as datetime_mock:
                                                datetime_mock.now.return_value = now
                                                datetime_mock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                                                response = await summary.get_overview(db=_OverviewDb())

        rain_gauge = response["data"]["rain_gauges"]["16132920"]
        runoff_station = response["data"]["runoff_stations"]["16132920"]
        self.assertIsNone(rain_gauge["rainfall"])
        self.assertIsNone(runoff_station["rainfall"])

    async def test_overview_computes_realtime_rainfall_from_latest_and_tenth_rain_records(self):
        now = datetime(2026, 5, 20, 23, 1, 40)

        class _OverviewDb:
            async def execute(self, query):
                text = str(query)
                if "FROM insect_records" in text or "FROM spore_records" in text or "FROM collect_logs" in text:
                    return _FakeExecuteResult([])
                if "max(insect_records.collection_time)" in text or "max(spore_records.collection_time)" in text:
                    return _FakeExecuteResult([None])
                return _FakeExecuteResult([])

        latest_rain_record = type("RainLike", (), {
            "device_code": "16132920",
            "collection_time": now,
            "rainfall": 113.0,
        })()
        rain_history = [latest_rain_record]
        for index, value in enumerate([110.0, 108.0, 107.0, 105.0, 103.0, 101.0, 99.0, 95.0], start=1):
            rain_history.append(type("RainLike", (), {
                "device_code": "16132920",
                "collection_time": now - timedelta(minutes=index * 10),
                "rainfall": value,
            })())
        tenth_rain_record = type("RainLike", (), {
            "device_code": "16132920",
            "collection_time": now - timedelta(minutes=90),
            "rainfall": 90.0,
        })()
        rain_history.append(tenth_rain_record)

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={"rain_16132920": "online"})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        async def fake_latest_records(_db, model, codes):
                            if model.__name__ == "RainfallRecord":
                                return {code: (latest_rain_record if code == "16132920" else None) for code in codes}
                            return {code: None for code in codes}

                        latest_ten_records = {
                            "16132920": rain_history,
                            "16132921": [],
                            "16132922": [],
                        }

                        with patch("routers.summary._get_latest_records_by_codes", new=AsyncMock(side_effect=fake_latest_records)):
                            with patch("routers.summary._get_latest_n_records_by_codes", new=AsyncMock(return_value=latest_ten_records), create=True):
                                with patch("routers.summary._get_latest_non_null_fields_by_codes", new=AsyncMock(return_value={})):
                                    with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                        with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                            with patch("routers.summary.datetime") as datetime_mock:
                                                datetime_mock.now.return_value = now
                                                datetime_mock.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                                                response = await summary.get_overview(db=_OverviewDb())

        rain_gauge = response["data"]["rain_gauges"]["16132920"]
        self.assertEqual(113.0, rain_gauge["rainfall"])
        self.assertEqual(23.0, rain_gauge["realtime_rainfall"])

    async def test_overview_keeps_runoff_rainfall_empty_without_matching_rain_gauge_code(self):
        now = datetime(2026, 5, 19, 23, 1, 40)

        class _OverviewDb:
            async def execute(self, query):
                text = str(query)
                if "FROM insect_records" in text or "FROM spore_records" in text or "FROM collect_logs" in text:
                    return _FakeExecuteResult([])
                if "max(insect_records.collection_time)" in text or "max(spore_records.collection_time)" in text:
                    return _FakeExecuteResult([None])
                return _FakeExecuteResult([])

        runoff_record = type("RunoffLike", (), {
            "device_code": "16132924",
            "collection_time": now,
            "flow_speed": 0.0,
            "flow_rate": 1.23,
            "total_flow": 0.0,
            "water_level": 0.0,
            "sand_content": 0.0,
            "liquid_pressure": 0.56,
            "runoff": 0.0,
            "rainfall": 999.0,
        })()

        with patch("routers.summary._get_device_statuses", new=AsyncMock(return_value={"runoff_16132924": "online"})):
            with patch("routers.summary.get_weather_support", new=AsyncMock(return_value={})):
                with patch("routers.summary.resolve_water_quality_codes", new=AsyncMock(return_value=[])):
                    with patch("routers.summary.get_latest_water_quality_record", new=AsyncMock(return_value=None)):
                        async def fake_latest_records(_db, model, codes):
                            if model.__name__ == "RunoffRecord":
                                return {code: (runoff_record if code == "16132924" else None) for code in codes}
                            return {code: None for code in codes}

                        with patch("routers.summary._get_latest_records_by_codes", new=AsyncMock(side_effect=fake_latest_records)):
                            with patch("routers.summary._get_latest_non_null_fields_by_codes", new=AsyncMock(return_value={})):
                                with patch("routers.summary._latest_non_empty_image", new=AsyncMock(return_value=None)):
                                    with patch("routers.summary._latest_valid_spore_image", new=AsyncMock(return_value=None)):
                                        response = await summary.get_overview(db=_OverviewDb())

        station = response["data"]["runoff_stations"]["16132924"]
        self.assertIsNone(station["rainfall"])
        self.assertIsNone(station["rainfall_source_code"])


if __name__ == "__main__":
    unittest.main()
