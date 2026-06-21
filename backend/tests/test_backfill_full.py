import sys
import unittest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import backfill_full  # noqa: E402


class WhxphBackfillTests(unittest.TestCase):
    def test_history_row_is_converted_to_latest_shape_with_element_names(self):
        row = {
            "facId": "16132920",
            "dataTime": "2026-05-09 17:30:41",
            "e1": 0,
            "e2": 12.5,
        }
        element_map = {
            "e1": {"eKey": "e1", "eName": "流速（m\\s）", "eUnit": " "},
            "e2": {"eKey": "e2", "eName": "雨量累计", "eUnit": "mm"},
        }

        shaped = backfill_full._whxph_history_row_to_latest_shape(row, "16132920", element_map)

        self.assertEqual("2026-05-09 17:30:41", shaped["datetime"])
        self.assertEqual("16132920", shaped["deviceId"])
        self.assertEqual("流速（m\\s）", shaped["eleLists"][0]["eName"])
        self.assertEqual("0", shaped["eleLists"][0]["eValue"])
        self.assertEqual("雨量累计", shaped["eleLists"][1]["eName"])
        self.assertEqual("12.5", shaped["eleLists"][1]["eValue"])

    def test_parse_whxph_collection_time_supports_history_and_latest_keys(self):
        self.assertEqual(
            datetime(2026, 5, 9, 17, 30, 41),
            backfill_full._parse_whxph_collection_time({"dataTime": "2026-05-09 17:30:41"}),
        )
        self.assertEqual(
            datetime(2026, 5, 9, 17, 30, 41),
            backfill_full._parse_whxph_collection_time({"datetime": "2026-05-09 17:30:41"}),
        )

    def test_delete_range_filters_by_codes_and_collection_time(self):
        async def run():
            db = MagicMock()
            result = MagicMock()
            result.rowcount = 7
            db.execute = AsyncMock(return_value=result)
            db.commit = AsyncMock()

            deleted = await backfill_full._delete_range(
                db,
                backfill_full.RainfallRecord,
                ["16132920", "16132921"],
                datetime(2026, 5, 1),
                datetime(2026, 5, 9),
            )

            self.assertEqual(7, deleted)
            db.execute.assert_awaited_once()
            db.commit.assert_awaited_once()

        asyncio.run(run())

    def test_delete_range_returns_zero_without_codes(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        async def run():
            return await backfill_full._delete_range(
                db,
                backfill_full.RainfallRecord,
                [],
                datetime(2026, 5, 1),
                datetime(2026, 5, 9),
            )

        self.assertEqual(0, asyncio.run(run()))
        db.execute.assert_not_called()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
