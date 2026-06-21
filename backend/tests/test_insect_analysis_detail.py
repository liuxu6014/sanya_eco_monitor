import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import InsectRecord  # noqa: E402
from models import SporeRecord  # noqa: E402
from routers import insect as insect_router  # noqa: E402
from routers.insect import get_combined_trend, get_insect_analysis_detail, get_insect_trend, get_species_stats, get_spore_analysis_detail  # noqa: E402


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


class InsectAnalysisDetailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        insect_router._insect_runtime_cache["value"].clear()
        insect_router._insect_runtime_cache["expires_at"].clear()

    async def test_focus_species_are_sorted_by_harm_score_descending(self):
        records = [
            InsectRecord(
                device_code="insect",
                collection_time=datetime.now(),
                total_count=1412,
                species_data={
                    "甜菜夜蛾": 284,
                    "二化螟": 246,
                    "金龟子": 426,
                    "水龟虫": 238,
                    "突背斑红蝽": 119,
                    "斜纹夜蛾": 60,
                    "瓜绢野螟": 90,
                    "甜菜白带野螟": 44,
                },
            )
        ]

        result = await get_insect_analysis_detail(species=None, days=30, db=_FakeDb(records))

        scores = [item["harm_score"] for item in result["data"]["focus_species"]]
        self.assertEqual(sorted(scores, reverse=True), scores)

    async def test_species_stats_include_all_species_in_period(self):
        records = [
            InsectRecord(
                device_code="insect",
                collection_time=datetime.now(),
                total_count=3,
                species_data={"甲虫": 1, "乙虫": 2},
            ),
            InsectRecord(
                device_code="insect",
                collection_time=datetime.now(),
                total_count=3,
                species_data={"丙虫": 3},
            ),
        ]

        result = await get_insect_analysis_detail(species=None, days=30, db=_FakeDb(records))

        self.assertEqual(
            {"甲虫": 1, "乙虫": 2, "丙虫": 3},
            {item["name"]: item["value"] for item in result["data"]["species_stats"]},
        )

    async def test_synthetic_zero_records_do_not_count_as_real_insect_data(self):
        now = datetime.now()
        records = [
            InsectRecord(
                device_code="202603172301",
                collection_time=now,
                total_count=0,
                species_data={},
                raw_data={"synthetic": True},
            ),
            InsectRecord(
                device_code="202603172301",
                collection_time=now,
                total_count=5,
                species_data={"甲虫": 5},
                raw_data={"source": "platform"},
            ),
        ]

        detail = await get_insect_analysis_detail(species=None, days=30, db=_FakeDb(records))
        trend = await get_insect_trend(days=30, db=_FakeDb(records))
        stats = await get_species_stats(days=30, db=_FakeDb(records))

        self.assertEqual(5, detail["data"]["summary"]["total_count"])
        self.assertEqual(1, detail["data"]["summary"]["active_days"])
        self.assertEqual([{"date": now.strftime("%Y-%m-%d"), "total": 5, "species": {"甲虫": 5}}], trend["data"])
        self.assertEqual([{"name": "甲虫", "value": 5}], stats["data"])


    async def test_combined_trend_uses_runtime_cache_for_same_days_parameter(self):
        now = datetime.now()
        records = [
            InsectRecord(
                device_code="202603172301",
                collection_time=now,
                total_count=5,
                species_data={"鐢茶櫕": 5},
                raw_data={"source": "platform"},
            ),
        ]

        with patch.object(insect_router.settings, "INSECT_SERIES_CACHE_SECONDS", 60):
            first = await get_combined_trend(days=30, db=_FakeDb(records))

            class _ExplodingDb:
                async def execute(self, _query):
                    raise AssertionError("database should not be queried on cached combined-trend call")

            second = await get_combined_trend(days=30, db=_ExplodingDb())

        self.assertEqual(first, second)

    async def test_spore_analysis_detail_uses_runtime_cache_for_same_days_parameter(self):
        now = datetime.now()
        records = [
            SporeRecord(
                device_code="202603172302",
                collection_time=now,
                total_count=3,
                spore_data={"孢子A": 3},
                image_url="https://example.com/spore.jpg",
                raw_data={"source": "platform"},
            ),
        ]

        with (
            patch.object(insect_router.settings, "INSECT_SERIES_CACHE_SECONDS", 60),
            patch("routers.insect.is_probably_black_image", new=AsyncMock(return_value=False)) as image_mock,
        ):
            first = await get_spore_analysis_detail(name=None, days=30, db=_FakeDb(records))

            class _ExplodingDb:
                async def execute(self, _query):
                    raise AssertionError("database should not be queried on cached spore-analysis-detail call")

            second = await get_spore_analysis_detail(name=None, days=30, db=_ExplodingDb())

        self.assertEqual(first, second)
        self.assertEqual(1, image_mock.await_count)


if __name__ == "__main__":
    unittest.main()
