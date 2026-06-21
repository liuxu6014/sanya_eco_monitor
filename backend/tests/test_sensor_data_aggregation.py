import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import RainfallRecord, RunoffRecord, WaterQualityRecord  # noqa: E402
from routers import sensor  # noqa: E402
from services.report_service import ReportService  # noqa: E402
from services.water_quality_support import resolve_water_quality_codes, water_metric_value  # noqa: E402


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


class _FakeDb:
    def __init__(self, records):
        self._records = records

    async def execute(self, _query):
        return _FakeExecuteResult(self._records)


class _FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeRowsDb:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _query):
        return _FakeRowsResult(self._rows)


class _ExplodingDb:
    async def execute(self, _query):
        raise AssertionError("db should not be hit when runtime cache is warm")


class SensorDataAggregationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sensor._sensor_runtime_cache["value"].clear()
        sensor._sensor_runtime_cache["expires_at"].clear()
    async def test_rainfall_daily_uses_last_daily_cumulative_reading_and_station_sum(self):
        complete_day = (datetime.now() - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RainfallRecord(device_code="a", collection_time=complete_day, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=complete_day + timedelta(minutes=5), rainfall=2.0),
            RainfallRecord(device_code="a", collection_time=complete_day + timedelta(minutes=10), rainfall=3.0),
            RainfallRecord(device_code="b", collection_time=complete_day, rainfall=0.0),
            RainfallRecord(device_code="b", collection_time=complete_day + timedelta(minutes=5), rainfall=10.0),
        ]

        result = await sensor.get_rainfall_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-2]

        self.assertEqual(complete_day.date().isoformat(), current_day["date"])
        self.assertEqual(13.0, current_day["rainfall"])
        self.assertEqual(10.0, current_day["station_peak"])

    async def test_rainfall_daily_exposes_per_device_daily_series(self):
        complete_day = (datetime.now() - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RainfallRecord(device_code="a", collection_time=complete_day, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=complete_day + timedelta(minutes=5), rainfall=2.0),
            RainfallRecord(device_code="a", collection_time=complete_day + timedelta(minutes=10), rainfall=3.0),
            RainfallRecord(device_code="b", collection_time=complete_day, rainfall=0.0),
            RainfallRecord(device_code="b", collection_time=complete_day + timedelta(minutes=5), rainfall=10.0),
        ]

        result = await sensor.get_rainfall_daily(days=7, db=_FakeDb(records))

        self.assertIn("by_device", result)
        self.assertEqual(3.0, result["by_device"]["a"][-2]["rainfall"])
        self.assertEqual(10.0, result["by_device"]["b"][-2]["rainfall"])

    async def test_rainfall_daily_includes_current_day_live_cumulative_reading(self):
        complete_day = (datetime.now() - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RainfallRecord(device_code="a", collection_time=complete_day, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=complete_day + timedelta(minutes=5), rainfall=3.0),
            RainfallRecord(device_code="a", collection_time=today, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=2.5),
        ]

        result = await sensor.get_rainfall_daily(days=7, db=_FakeDb(records))

        self.assertEqual(today.date().isoformat(), result["data"][-1]["date"])
        self.assertEqual(2.5, result["data"][-1]["rainfall"])

    async def test_report_rainfall_summary_uses_same_last_daily_cumulative_reading_and_station_sum(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RainfallRecord(device_code="a", collection_time=today, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=2.0),
            RainfallRecord(device_code="a", collection_time=today + timedelta(minutes=10), rainfall=3.0),
            RainfallRecord(device_code="b", collection_time=today, rainfall=0.0),
            RainfallRecord(device_code="b", collection_time=today + timedelta(minutes=5), rainfall=10.0),
        ]

        summary = await ReportService()._aggregate_rainfall(
            _FakeDb(records),
            today.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(5, summary["records_count"])
        self.assertEqual(13.0, summary["total_rainfall"])
        self.assertEqual([{"date": today.date().isoformat(), "rainfall": 13.0}], summary["daily"])

    async def test_report_runoff_summary_ignores_total_flow_delta_with_only_tiny_level_blips(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=161.0, runoff=0, flow_rate=0, water_level=0.02),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=0.0, runoff=0, flow_rate=0, water_level=0.02),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=7.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=15), total_flow=0.007, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=20), total_flow=0.7, runoff=0, flow_rate=0, water_level=0.01),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            today.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(0.0, summary["total_runoff"])
        self.assertEqual(0.0, summary["by_device"]["a"]["total_runoff"])

    async def test_report_runoff_summary_sums_clean_daily_deltas_like_daily_chart(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        records = [
            RunoffRecord(device_code="a", collection_time=yesterday, total_flow=100, runoff=0.1),
            RunoffRecord(device_code="a", collection_time=yesterday + timedelta(minutes=5), total_flow=105, runoff=0.1),
            RunoffRecord(device_code="a", collection_time=today, total_flow=1, runoff=0.1),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=3, runoff=0.1),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            yesterday.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(7.0, summary["total_runoff"])
        self.assertEqual(7.0, summary["by_device"]["a"]["total_runoff"])
        self.assertEqual(3.0, summary["by_device"]["a"]["total_flow_latest"])

    async def test_report_runoff_summary_requires_hydrology_support_per_day(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        records = [
            RunoffRecord(device_code="a", collection_time=yesterday, total_flow=0, runoff=0, flow_rate=0, water_level=0.02),
            RunoffRecord(device_code="a", collection_time=yesterday + timedelta(minutes=5), total_flow=7, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today, total_flow=1, runoff=0.1),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=1.3, runoff=0.1),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            yesterday.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(0.3, summary["total_runoff"])
        self.assertEqual(0.3, summary["by_device"]["a"]["total_runoff"])
        self.assertEqual(1.3, summary["by_device"]["a"]["total_flow_latest"])

    async def test_report_water_quality_uses_cod_when_permanganate_column_is_empty(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            WaterQualityRecord(
                device_code="16133028",
                collection_time=today,
                ammonia_nitrogen=1,
                total_phosphorus=2,
                total_nitrogen=3,
                permanganate_index=None,
                raw_data={"eleLists": [{"eName": "COD", "eValue": "78.66", "unit": "mg/L"}]},
            )
        ]

        with (
            patch("services.report_service.resolve_water_quality_codes", AsyncMock(return_value=["16133028"])),
            patch("services.report_service.get_water_quality_records", AsyncMock(return_value=records)),
        ):
            summary = await ReportService()._aggregate_water_quality(
                db=None,
                start_dt=today.replace(hour=0, minute=0),
                end_dt=today.replace(hour=23, minute=59),
            )

        self.assertEqual(78.66, summary["avg_permanganate"])

    async def test_runoff_daily_uses_last_station_cumulative_rainfall_readings(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, rainfall=1000, runoff=0.1, total_flow=5),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=1010, runoff=0.1, total_flow=8),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), rainfall=1010, runoff=0.1, total_flow=8),
            RunoffRecord(device_code="b", collection_time=today, rainfall=300, runoff=0.2, total_flow=2),
            RunoffRecord(device_code="b", collection_time=today + timedelta(minutes=5), rainfall=320, runoff=0.2, total_flow=7),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(today.date().isoformat(), current_day["date"])
        self.assertEqual(1330.0, current_day["rainfall"])
        self.assertEqual(8.0, current_day["runoff"])
        self.assertEqual(15.0, current_day["total_flow"])
        self.assertEqual(0.14, current_day["runoff_rate"])
        self.assertEqual(1010.0, result["by_device"]["a"][-1]["rainfall"])
        self.assertEqual(320.0, result["by_device"]["b"][-1]["rainfall"])
        self.assertEqual(8.0, result["by_device"]["a"][-1]["total_flow"])
        self.assertEqual(7.0, result["by_device"]["b"][-1]["total_flow"])

    async def test_runoff_daily_keeps_raw_outlier_metrics_visible_but_does_not_treat_raw_runoff_as_cumulative_volume(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(
                device_code="a",
                collection_time=today,
                runoff=32.767,
                sand_content=32.767,
                flow_rate=327.67,
                flow_speed=327.67,
                water_level=327.67,
                liquid_pressure=327.67,
            ),
            RunoffRecord(
                device_code="b",
                collection_time=today,
                runoff=0.25,
                sand_content=0.013,
                flow_rate=1.25,
                flow_speed=0.31,
                water_level=0.42,
                liquid_pressure=12.5,
            ),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))

        self.assertIn("by_device", result)
        self.assertEqual(0, result["by_device"]["a"][-1]["runoff"])
        self.assertEqual(32.767, result["by_device"]["a"][-1]["sand"])
        self.assertEqual(327.67, result["by_device"]["a"][-1]["flow"])
        self.assertEqual(0, result["by_device"]["b"][-1]["runoff"])
        self.assertEqual(0.013, result["by_device"]["b"][-1]["sand"])
        self.assertTrue(result["has_anomaly"])
        self.assertTrue(result["anomaly_summary"]["has_anomaly"])
        self.assertIn("原始值", result["anomaly_summary"]["message"])
        self.assertEqual("sand", result["by_device"]["a"][-1]["anomaly_flags"][0]["metric"])

    async def test_runoff_daily_keeps_small_rainfall_increment_visible(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, rainfall=0.0, total_flow=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=0.0, total_flow=0),
            RunoffRecord(device_code="b", collection_time=today, rainfall=0.0, total_flow=0),
            RunoffRecord(device_code="b", collection_time=today + timedelta(minutes=5), rainfall=0.2, total_flow=0),
            RunoffRecord(device_code="c", collection_time=today, rainfall=0.0, total_flow=0),
            RunoffRecord(device_code="c", collection_time=today + timedelta(minutes=5), rainfall=0.2, total_flow=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0.4, current_day["rainfall"])

    async def test_runoff_daily_does_not_fallback_to_raw_runoff_when_counter_delta_is_invalid(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=161, runoff=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=32767, runoff=327.67),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=161, runoff=0),
            RunoffRecord(device_code="b", collection_time=today, total_flow=30, runoff=0),
            RunoffRecord(device_code="b", collection_time=today + timedelta(minutes=5), total_flow=30, runoff=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0, current_day["runoff"])
        self.assertEqual(191.0, current_day["total_flow"])

    async def test_runoff_daily_ignores_raw_runoff_when_counter_plateau_returns_to_baseline(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=0.9, runoff=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=15), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=20), total_flow=0.0, runoff=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0, current_day["runoff"])
        self.assertEqual(0, current_day["total_flow"])

    async def test_runoff_daily_keeps_raw_outlier_series_values_visible(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(
                device_code="a",
                collection_time=today,
                runoff=32.767,
                sand_content=32.767,
                flow_rate=327.67,
                flow_speed=327.67,
                water_level=327.67,
                liquid_pressure=327.67,
            ),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(32.77, current_day["sand"])
        self.assertEqual(327.67, current_day["flow"])
        self.assertEqual(327.67, current_day["flow_speed"])
        self.assertEqual(327.67, current_day["water_level"])
        self.assertEqual(327.7, current_day["liquid_pressure"])
        self.assertEqual(0, current_day["runoff"])

    async def test_runoff_daily_ignores_total_flow_delta_without_hydrology_support(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=0.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=7.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=0.007, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=15), total_flow=0.7, runoff=0, flow_rate=0, water_level=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0, current_day["runoff"])
        self.assertEqual(0.7, current_day["total_flow"])

    async def test_runoff_daily_ignores_total_flow_delta_with_only_tiny_level_blips(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=161.0, runoff=0, flow_rate=0, water_level=0.02),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=0.0, runoff=0, flow_rate=0, water_level=0.02),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=7.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=15), total_flow=0.007, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=20), total_flow=0.7, runoff=0, flow_rate=0, water_level=0.01),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0, current_day["runoff"])
        self.assertEqual(0.7, current_day["total_flow"])

    async def test_runoff_daily_uses_raw_runoff_for_device_rows_when_total_flow_counter_is_flat(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="zero-a", collection_time=today, total_flow=0.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="zero-b", collection_time=today, total_flow=8.0, runoff=0, flow_rate=0, water_level=0),
            RunoffRecord(device_code="fallback-a", collection_time=today, total_flow=1.1, runoff=786.408, flow_rate=32.767, water_level=0),
            RunoffRecord(device_code="fallback-b", collection_time=today, total_flow=0.0, runoff=786.408, flow_rate=32.767, water_level=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]

        self.assertEqual(0, current_day["runoff"])
        self.assertEqual(9.1, current_day["total_flow"])
        self.assertEqual(393.204, current_day["runoff_rate"])
        self.assertEqual(786.408, result["by_device"]["fallback-a"][-1]["runoff"])
        self.assertEqual(786.408, result["by_device"]["fallback-b"][-1]["runoff"])
        self.assertEqual(786.408, result["by_device"]["fallback-a"][-1]["runoff_rate"])
        self.assertEqual(786.408, result["by_device"]["fallback-b"][-1]["runoff_rate"])

    async def test_runoff_daily_keeps_plateau_counter_days_visible_in_device_series(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=1.1, runoff=786.408, flow_rate=32.767, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=1.1, runoff=786.408, flow_rate=32.767, water_level=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=1.1, runoff=786.408, flow_rate=32.767, water_level=0),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))

        self.assertEqual(786.408, result["by_device"]["a"][-1]["runoff"])
        self.assertEqual(786.408, result["by_device"]["a"][-1]["runoff_rate"])
        self.assertEqual(1.1, result["by_device"]["a"][-1]["total_flow"])
        self.assertEqual(0, result["data"][-1]["runoff"])
        self.assertEqual(1.1, result["data"][-1]["total_flow"])
        self.assertEqual(786.408, result["data"][-1]["runoff_rate"])

    async def test_runoff_daily_uses_latest_cumulative_total_flow_even_when_other_hydrology_metrics_are_zero(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(
                device_code="16132921",
                collection_time=today,
                rainfall=5.8,
                total_flow=19.9,
                runoff=0.0,
                flow_rate=0.0,
                water_level=0.0,
                liquid_pressure=0.06,
            ),
            RunoffRecord(
                device_code="16132921",
                collection_time=today + timedelta(minutes=5),
                rainfall=5.8,
                total_flow=19.9,
                runoff=0.0,
                flow_rate=0.0,
                water_level=0.0,
                liquid_pressure=0.06,
            ),
        ]

        result = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
        current_day = result["data"][-1]
        device_day = result["by_device"]["16132921"][-1]

        self.assertEqual(19.9, current_day["total_flow"])
        self.assertEqual(19.9, device_day["total_flow"])
        self.assertEqual(0, current_day["runoff"])

    async def test_report_runoff_summary_keeps_raw_outlier_metrics_visible(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(
                device_code="a",
                collection_time=today,
                runoff=32.767,
                sand_content=32.767,
                flow_rate=327.67,
                flow_speed=327.67,
                water_level=327.67,
                liquid_pressure=327.67,
            ),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            today.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertIsNone(summary["avg_flow_rate"])
        self.assertIsNone(summary["max_flow_rate"])
        self.assertIsNone(summary["avg_water_level"])
        self.assertIsNone(summary["by_device"]["a"]["avg_sand_content"])
        self.assertIsNone(summary["by_device"]["a"]["avg_flow_rate"])
        self.assertIsNone(summary["by_device"]["a"]["avg_flow_speed"])
        self.assertIsNone(summary["by_device"]["a"]["avg_water_level"])
        self.assertIsNone(summary["by_device"]["a"]["avg_liquid_pressure"])
        self.assertEqual(0.0, summary["by_device"]["a"]["total_runoff"])

    async def test_report_runoff_summary_uses_latest_cumulative_values_and_last_daily_rainfall_readings(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, rainfall=1000, runoff=0.1, total_flow=5),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=1010, runoff=0.1, total_flow=8),
            RunoffRecord(device_code="b", collection_time=today, rainfall=300, runoff=0.2, total_flow=2),
            RunoffRecord(device_code="b", collection_time=today + timedelta(minutes=5), rainfall=320, runoff=0.2, total_flow=7),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            today.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(8.0, summary["by_device"]["a"]["total_flow_latest"])
        self.assertEqual(7.0, summary["by_device"]["b"]["total_flow_latest"])
        self.assertEqual(1010.0, summary["by_device"]["a"]["total_rainfall"])
        self.assertEqual(320.0, summary["by_device"]["b"]["total_rainfall"])

    async def test_report_runoff_summary_does_not_treat_raw_runoff_as_cumulative_volume(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, total_flow=0.9, runoff=0),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=10), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=15), total_flow=3276.7, runoff=32.767),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=20), total_flow=0.0, runoff=0),
        ]

        summary = await ReportService()._aggregate_runoff(
            _FakeDb(records),
            today.replace(hour=0, minute=0),
            today.replace(hour=23, minute=59),
        )

        self.assertEqual(0.0, summary["by_device"]["a"]["total_runoff"])

    async def test_water_quality_daily_uses_cod_when_permanganate_column_is_empty(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            WaterQualityRecord(
                device_code="16116030",
                collection_time=today,
                ammonia_nitrogen=18.98,
                total_phosphorus=0.201,
                total_nitrogen=0.187,
                permanganate_index=None,
                raw_data={"eleLists": [{"eName": "COD", "eValue": "78.66", "unit": "mg/L"}]},
            )
        ]

        with (
            patch.object(sensor, "resolve_water_quality_codes", AsyncMock(return_value=["16116030"])),
            patch.object(sensor, "get_water_quality_records", AsyncMock(return_value=records)),
        ):
            result = await sensor.get_wq_daily(days=7, db=None)

        current_day = result["data"][-1]

        self.assertEqual(today.date().isoformat(), current_day["date"])
        self.assertEqual(78.66, current_day["permanganate"])

    def test_water_metric_value_uses_cod_fallback_for_latest_panel_and_scores(self):
        record = WaterQualityRecord(
            device_code="16116030",
            collection_time=datetime.now(),
            permanganate_index=None,
            raw_data={"eleLists": [{"eName": "COD", "eValue": "78.66", "unit": "mg/L"}]},
        )

        self.assertEqual(78.66, water_metric_value(record, "permanganate_index", "permanganate"))

    async def test_configured_water_quality_code_is_used_even_when_other_code_has_more_records(self):
        rows = [("16116030", 2397, datetime.now())]

        codes = await resolve_water_quality_codes(
            _FakeRowsDb(rows),
            preferred_code="16133028",
        )

        self.assertEqual([], codes)

    async def test_water_quality_analysis_works_when_only_non_preferred_code_has_recent_data(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            WaterQualityRecord(
                device_code="16116030",
                collection_time=today,
                ammonia_nitrogen=0.8,
                total_phosphorus=0.12,
                total_nitrogen=0.9,
                permanganate_index=4.6,
                raw_data={},
            )
        ]

        with (
            patch.object(sensor, "resolve_water_quality_codes", AsyncMock(return_value=["16116030"])),
            patch.object(sensor, "get_water_quality_records", AsyncMock(return_value=records)),
        ):
            result = await sensor.get_water_quality_analysis(days=30, db=None)

        self.assertEqual("16116030", records[0].device_code)
        self.assertEqual("常规监测", result["data"]["summary"]["risk_level"])
        self.assertEqual("高锰酸盐指数", result["data"]["metrics"][0]["label"])

    async def test_runoff_daily_uses_runtime_cache_for_same_days_parameter(self):
        today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(device_code="a", collection_time=today, rainfall=1000, runoff=0.1, total_flow=5),
            RunoffRecord(device_code="a", collection_time=today + timedelta(minutes=5), rainfall=1010, runoff=0.1, total_flow=8),
        ]

        with patch.object(sensor.settings, "SENSOR_SERIES_CACHE_SECONDS", 60):
            first = await sensor.get_runoff_daily(days=7, db=_FakeDb(records))
            second = await sensor.get_runoff_daily(days=7, db=_ExplodingDb())

        self.assertEqual(first, second)

    async def test_runoff_analysis_uses_runtime_cache_for_same_days_parameter(self):
        payload = {"data": {"summary": {"risk_score": 12}, "daily": []}}

        with (
            patch.object(sensor.settings, "SENSOR_SERIES_CACHE_SECONDS", 60),
            patch.object(sensor, "get_runoff_daily", AsyncMock(return_value={"data": []})) as daily_mock,
        ):
            first = await sensor.get_runoff_analysis(days=30, db=None)
            second = await sensor.get_runoff_analysis(days=30, db=None)

        self.assertEqual(first, second)
        self.assertEqual(1, daily_mock.await_count)

    async def test_rainfall_analysis_uses_runtime_cache_for_same_days_parameter(self):
        with (
            patch.object(sensor.settings, "SENSOR_SERIES_CACHE_SECONDS", 60),
            patch.object(
                sensor,
                "get_rainfall_daily",
                AsyncMock(
                    return_value={
                        "data": [
                            {"date": "2026-05-01", "rainfall": 12.3, "max_hourly": 4.5, "station_peak": 6.7},
                            {"date": "2026-05-02", "rainfall": 0, "max_hourly": 0, "station_peak": 0},
                        ]
                    }
                ),
            ) as daily_mock,
        ):
            first = await sensor.get_rainfall_analysis(days=30, db=None)
            second = await sensor.get_rainfall_analysis(days=30, db=None)

        self.assertEqual(first, second)
        self.assertEqual(1, daily_mock.await_count)

    async def test_water_quality_analysis_uses_runtime_cache_for_same_days_parameter(self):
        with (
            patch.object(sensor.settings, "SENSOR_SERIES_CACHE_SECONDS", 60),
            patch.object(
                sensor,
                "get_wq_daily",
                AsyncMock(
                    return_value={
                        "data": [
                            {"date": "2026-05-01", "permanganate": 4.6, "tn": 0.8, "tp": 0.12, "nh4n": 0.5},
                            {"date": "2026-05-02", "permanganate": 4.2, "tn": 0.7, "tp": 0.1, "nh4n": 0.4},
                        ]
                    }
                ),
            ) as daily_mock,
        ):
            first = await sensor.get_water_quality_analysis(days=30, db=None)
            second = await sensor.get_water_quality_analysis(days=30, db=None)

        self.assertEqual(first, second)
        self.assertEqual(1, daily_mock.await_count)


if __name__ == "__main__":
    unittest.main()
