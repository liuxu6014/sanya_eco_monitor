import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import SporeRecord  # noqa: E402
from services.report_service import ReportService  # noqa: E402


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


class ReportCaptureImagesTests(unittest.IsolatedAsyncioTestCase):
    async def test_spore_summary_does_not_use_out_of_period_fallback_images(self):
        service = ReportService()
        start = datetime(2026, 5, 3)
        end = datetime(2026, 5, 9, 23, 59, 59)
        records = [
            SporeRecord(
                device_code="spore-1",
                collection_time=start + timedelta(days=1),
                total_count=3,
                spore_data={"孢子": 3},
                image_url=None,
            )
        ]

        with patch.object(service, "_fallback_capture_images", new=AsyncMock(return_value=[{"url": "outside.jpg"}])) as fallback:
            summary = await service._aggregate_spore(_FakeDb(records), start, end)

        fallback.assert_not_awaited()
        self.assertEqual([], summary["capture_images"])

    async def test_spore_summary_filters_black_images(self):
        service = ReportService()
        start = datetime(2026, 5, 3)
        end = datetime(2026, 5, 9, 23, 59, 59)
        records = [
            SporeRecord(
                device_code="spore-1",
                collection_time=start + timedelta(days=1),
                total_count=3,
                spore_data={"孢子": 3},
                image_url="https://example.com/black.jpg",
            ),
            SporeRecord(
                device_code="spore-1",
                collection_time=start + timedelta(days=2),
                total_count=4,
                spore_data={"孢子": 4},
                image_url="https://example.com/normal.jpg",
            ),
        ]

        with patch("services.report_service.is_probably_black_image", new=AsyncMock(side_effect=[True, False])):
            summary = await service._aggregate_spore(_FakeDb(records), start, end)

        self.assertEqual(1, len(summary["capture_images"]))
        self.assertEqual("https://example.com/normal.jpg", summary["capture_images"][0]["url"])


if __name__ == "__main__":
    unittest.main()
