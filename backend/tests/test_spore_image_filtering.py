import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import SporeRecord  # noqa: E402
from routers import insect  # noqa: E402


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


class SporeImageFilteringTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_spore_falls_back_to_latest_non_black_image(self):
        now = datetime(2026, 5, 13, 10, 0, 0)
        records = [
            SporeRecord(
                id=1,
                device_code="spore-1",
                collection_time=now,
                total_count=5,
                spore_data={"瀛㈠瓙": 5},
                image_url="https://example.com/black-latest.jpg",
            ),
            SporeRecord(
                id=2,
                device_code="spore-1",
                collection_time=now - timedelta(hours=1),
                total_count=4,
                spore_data={"瀛㈠瓙": 4},
                image_url="https://example.com/normal-previous.jpg",
            ),
        ]

        with patch("routers.insect.is_probably_black_image", new=AsyncMock(side_effect=[True, False])):
            response = await insect.get_latest_spore(db=_FakeDb(records))

        payload = response["data"]
        self.assertEqual("https://example.com/normal-previous.jpg", payload["image_url"])
        self.assertEqual((now - timedelta(hours=1)).isoformat(), payload["image_collection_time"])

    async def test_spore_images_filters_black_images(self):
        now = datetime(2026, 5, 13, 10, 0, 0)
        records = [
            SporeRecord(
                id=1,
                device_code="spore-1",
                collection_time=now,
                total_count=5,
                spore_data={"瀛㈠瓙": 5},
                image_url="https://example.com/black.jpg",
            ),
            SporeRecord(
                id=2,
                device_code="spore-1",
                collection_time=now - timedelta(hours=1),
                total_count=4,
                spore_data={"瀛㈠瓙": 4},
                image_url="https://example.com/normal.jpg",
            ),
        ]

        with patch("routers.insect.is_probably_black_image", new=AsyncMock(side_effect=[True, False])):
            response = await insect.get_spore_images(days=30, db=_FakeDb(records))

        payload = response["data"]
        self.assertEqual(1, len(payload))
        self.assertEqual("https://example.com/normal.jpg", payload[0]["image_url"])

    async def test_spore_analysis_detail_filters_black_images_from_gallery_and_latest(self):
        now = datetime(2026, 5, 13, 10, 0, 0)
        records = [
            SporeRecord(
                id=1,
                device_code="spore-1",
                collection_time=now - timedelta(days=1),
                total_count=2,
                spore_data={"孢子": 2},
                image_url="https://example.com/black.jpg",
            ),
            SporeRecord(
                id=2,
                device_code="spore-1",
                collection_time=now,
                total_count=5,
                spore_data={"孢子": 5},
                image_url="https://example.com/normal.jpg",
            ),
        ]

        with patch("routers.insect.is_probably_black_image", new=AsyncMock(side_effect=[True, False])):
            with patch("routers.insect.datetime") as mock_datetime:
                mock_datetime.now.return_value = now
                mock_datetime.combine.side_effect = datetime.combine
                response = await insect.get_spore_analysis_detail(days=30, db=_FakeDb(records))

        payload = response["data"]
        self.assertEqual("https://example.com/normal.jpg", payload["latest_image"]["image_url"])
        self.assertEqual(1, len(payload["images"]))
        self.assertEqual("https://example.com/normal.jpg", payload["images"][0]["image_url"])


if __name__ == "__main__":
    unittest.main()
