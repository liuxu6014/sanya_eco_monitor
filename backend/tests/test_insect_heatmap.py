import sys
import unittest
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.insect import get_species_heatmap  # noqa: E402


class _FakeScalarResult:
    def all(self):
        return []


class _FakeExecuteResult:
    def scalars(self):
        return _FakeScalarResult()


class _FakeDb:
    async def execute(self, _query):
        return _FakeExecuteResult()


class InsectHeatmapTests(unittest.IsolatedAsyncioTestCase):
    async def test_heatmap_returns_full_requested_day_axis_without_records(self):
        result = await get_species_heatmap(days=14, db=_FakeDb())

        dates = result["data"]["dates"]

        self.assertEqual(14, len(dates))
        self.assertEqual(datetime.now().strftime("%m-%d"), dates[-1])
        self.assertEqual([], result["data"]["species"])
        self.assertEqual([], result["data"]["values"])


if __name__ == "__main__":
    unittest.main()
