import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import InsectRecord, RainfallRecord, RunoffRecord, WaterQualityRecord  # noqa: E402
from services import guideline_metrics  # noqa: E402
from services.warning_rules import build_warning_analysis  # noqa: E402


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


class GuidelineMetricsTests(unittest.IsolatedAsyncioTestCase):
    def _warning_by_key(self, analysis, key):
        return next(item for item in analysis["indicator_warnings"] if item["key"] == key)

    async def test_pest_monitoring_days_count_zero_capture_records_as_valid_data(self):
        now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            InsectRecord(collection_time=now - timedelta(days=2), device_code="insect", total_count=0, species_data={}),
            InsectRecord(collection_time=now - timedelta(days=1), device_code="insect", total_count=5, species_data={"金龟子": 5}),
            InsectRecord(collection_time=now, device_code="insect", total_count=0, species_data={}),
        ]

        with patch.object(guideline_metrics, "derive_pest_risk_level", return_value="低"):
            result = await guideline_metrics._build_pest_management_metrics(
                _FakeDb(records),
                recent_days=30,
            )

        self.assertEqual(3, result["active_insect_days"])
        self.assertEqual(1, result["positive_insect_days"])
        self.assertEqual(5, result["total_insects"])

    async def test_water_baseline_days_use_available_data_range_not_today(self):
        first = datetime(2026, 4, 20, 11, 35)
        records = [
            WaterQualityRecord(
                collection_time=first,
                device_code="16133028",
                ammonia_nitrogen=1,
                total_phosphorus=1,
                total_nitrogen=1,
                permanganate_index=1,
            ),
            WaterQualityRecord(
                collection_time=first + timedelta(days=4),
                device_code="16133028",
                ammonia_nitrogen=2,
                total_phosphorus=2,
                total_nitrogen=2,
                permanganate_index=2,
            ),
        ]

        with patch.object(guideline_metrics, "resolve_water_quality_codes", AsyncMock(return_value=["16133028"])), patch.object(
            guideline_metrics,
            "get_water_quality_records",
            AsyncMock(return_value=records),
        ):
            result = await guideline_metrics._build_water_quality_metrics(
                _FakeDb(records),
                recent_days=30,
            )

        self.assertEqual(5, result["baseline_period"]["days"])
        self.assertEqual("2026-04-20", result["baseline_period"]["start"])
        self.assertEqual("2026-04-24", result["baseline_period"]["end"])

    async def test_rainfall_device_metrics_use_recent_complete_days(self):
        now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0)
        today = now.replace(hour=0, minute=0)
        # 雨量计为当日累计（每日归零），当日最后一条读数即当日降雨量；区域降雨取各站求和。
        records = [
            RainfallRecord(device_code="a", collection_time=yesterday, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=yesterday + timedelta(hours=1), rainfall=12.0),
            RainfallRecord(device_code="b", collection_time=yesterday, rainfall=0.0),
            RainfallRecord(device_code="b", collection_time=yesterday + timedelta(hours=1), rainfall=6.0),
            # 今日数据不完整，应被排除（仅统计完整日）。
            RainfallRecord(device_code="a", collection_time=today, rainfall=0.0),
            RainfallRecord(device_code="a", collection_time=today + timedelta(hours=1), rainfall=100.0),
        ]

        result = await guideline_metrics._build_rainfall_device_metrics(
            _FakeDb(records),
            recent_days=2,
        )

        self.assertTrue(result["available"])
        self.assertEqual(yesterday.date().isoformat(), result["summary"]["peak"]["date"])
        self.assertEqual(18.0, result["summary"]["peak"]["rainfall"])
        self.assertEqual(1, result["summary"]["rainy_days"])

    async def test_warning_rainfall_uses_device_data_not_weather_history(self):
        analysis = build_warning_analysis(
            recent_days=30,
            pest_management={
                "insect_peak": {"date": "2026-05-01", "count": 0},
                "spore_peak": {"date": "2026-05-01", "count": 0},
                "top_species": {},
            },
            runoff_erosion={"highest_risk_station": {}, "reference_station": {}},
            weather_support={
                "history_daily": [{"date": "2026-05-01", "precip": 99.0}],
                "history_summary": {"days": 30, "total_precip": 99.0, "rainy_days": 1},
            },
            rainfall_device_metrics={
                "available": True,
                "period_days": 30,
                "summary": {
                    "peak": {"date": "2026-05-02", "rainfall": 12.3},
                    "total_rainfall": 12.3,
                    "rainy_days": 1,
                },
            },
        )

        rainfall_warning = self._warning_by_key(analysis, "rainfall_peak")
        self.assertEqual(12.3, rainfall_warning["current_value"])
        self.assertEqual("rain_gauge_device", rainfall_warning["supporting"]["source"])
        self.assertEqual("2026-05-02", rainfall_warning["supporting"]["peak_date"])

    async def test_warning_rainfall_is_unavailable_without_device_data(self):
        analysis = build_warning_analysis(
            recent_days=30,
            pest_management={
                "insect_peak": {"date": "2026-05-01", "count": 0},
                "spore_peak": {"date": "2026-05-01", "count": 0},
                "top_species": {},
            },
            runoff_erosion={"highest_risk_station": {}, "reference_station": {}},
            weather_support={
                "history_daily": [{"date": "2026-05-01", "precip": 99.0}],
                "history_summary": {"days": 30, "total_precip": 99.0, "rainy_days": 1},
            },
            rainfall_device_metrics={"available": False, "period_days": 30},
        )

        rainfall_warning = self._warning_by_key(analysis, "rainfall_peak")
        self.assertFalse(rainfall_warning["available"])
        self.assertIsNone(rainfall_warning["current_value"])

    async def test_runoff_metrics_keep_raw_sand_content_for_interface_alignment(self):
        now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        records = [
            RunoffRecord(
                collection_time=now - timedelta(hours=2),
                device_code="16132925",
                flow_rate=0.0,
                runoff=0.0,
                sand_content=0.0,
                rainfall=0.0,
            ),
            RunoffRecord(
                collection_time=now - timedelta(hours=1),
                device_code="16132925",
                flow_rate=0.0,
                runoff=0.0,
                sand_content=0.0,
                rainfall=0.0,
            ),
            RunoffRecord(
                collection_time=now,
                device_code="16132925",
                flow_rate=327.67,
                runoff=32.767,
                sand_content=32.767,
                rainfall=0.0,
            ),
        ]

        result = await guideline_metrics._build_runoff_metrics(
            _FakeDb(records),
            recent_days=30,
        )

        self.assertEqual(10.9223, result["highest_risk_station"]["avg_sand_content"])
        self.assertEqual(10.9223, result["highest_risk_station"]["avg_runoff"])
        self.assertEqual(109.2233, result["highest_risk_station"]["avg_flow_rate"])
        self.assertEqual("16132925", result["highest_sand_station"]["device_code"])
        self.assertTrue(result["anomaly_summary"]["has_anomaly"])
        self.assertIn("原始值", result["anomaly_summary"]["message"])
        self.assertTrue(result["highest_risk_station"]["has_anomaly"])

    async def test_warning_sand_station_uses_highest_sand_station(self):
        analysis = build_warning_analysis(
            recent_days=30,
            pest_management={
                "insect_peak": {"date": "2026-05-01", "count": 0},
                "spore_peak": {"date": "2026-05-01", "count": 0},
                "top_species": {},
            },
            runoff_erosion={
                "highest_risk_station": {"name": "芒果林径流点2", "avg_sand_content": 0.0},
                "highest_sand_station": {"name": "槟榔林径流点", "avg_sand_content": 0.0128},
                "reference_station": {"name": "次生林径流点"},
            },
            weather_support={"history_summary": {"days": 30}},
            rainfall_device_metrics={"available": False, "period_days": 30},
        )

        sand_warning = self._warning_by_key(analysis, "sand_content")
        self.assertEqual(0.0128, sand_warning["current_value"])
        self.assertIn("槟榔林径流点", sand_warning["summary"])
        self.assertNotIn("芒果林径流点2，平均含沙量0", sand_warning["summary"])


if __name__ == "__main__":
    unittest.main()
