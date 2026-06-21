import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Base  # noqa: E402
import models  # noqa: E402,F401  (ensure tables registered)
from models import DeviceStatusEvent, RainfallRecord  # noqa: E402
from services import device_uptime  # noqa: E402


class GapReconstructionTests(unittest.TestCase):
    def test_reconstruct_gaps_detects_internal_and_trailing(self):
        now = datetime(2026, 6, 21, 12, 0, 0)
        expected = timedelta(minutes=30)
        threshold = timedelta(minutes=90)
        base = datetime(2026, 6, 20, 9, 0, 0)
        # 9:00–11:00 每30分钟一条，然后断到 14:00，再两条，之后再无数据直到 now。
        timestamps = [base + timedelta(minutes=30 * i) for i in range(5)]  # 9:00..11:00
        timestamps += [base + timedelta(hours=5), base + timedelta(hours=5, minutes=30)]  # 14:00, 14:30

        gaps = device_uptime.reconstruct_gaps(
            timestamps,
            range_start=base,
            range_end=now,
            expected=expected,
            threshold=threshold,
            now=now,
        )

        # 内部空档：11:00+30min=11:30 → 14:00
        self.assertIn((base + timedelta(hours=2, minutes=30), base + timedelta(hours=5)), gaps)
        # 末尾空档：14:30+30min=15:00 → now
        self.assertIn((base + timedelta(hours=6), now), gaps)

    def test_merge_intervals_unions_overlaps(self):
        a = (datetime(2026, 6, 1, 0, 0), datetime(2026, 6, 1, 2, 0))
        b = (datetime(2026, 6, 1, 1, 0), datetime(2026, 6, 1, 3, 0))
        c = (datetime(2026, 6, 1, 5, 0), datetime(2026, 6, 1, 6, 0))
        merged = device_uptime._merge_intervals([a, b, c])
        self.assertEqual(
            [
                (datetime(2026, 6, 1, 0, 0), datetime(2026, 6, 1, 3, 0)),
                (datetime(2026, 6, 1, 5, 0), datetime(2026, 6, 1, 6, 0)),
            ],
            merged,
        )


class DeviceUptimeDbTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = TemporaryDirectory()
        path = Path(self._tmp.name) / "uptime-test.db"
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmp.cleanup()

    async def _insert_rain(self, session, code, times):
        for idx, t in enumerate(times):
            session.add(RainfallRecord(device_code=code, collection_time=t, rainfall=float(idx)))
        await session.commit()

    async def test_internal_gap_is_reported_as_outage(self):
        code = "16132920"
        now = datetime(2026, 6, 21, 12, 0, 0)
        # 连续两天每30分钟一条，但 6-20 10:00 之后断了 4 小时。
        day = datetime(2026, 6, 20, 6, 0, 0)
        times = [day + timedelta(minutes=30 * i) for i in range(9)]  # 6:00..10:00
        times += [day + timedelta(hours=8) + timedelta(minutes=30 * i) for i in range(20)]  # 14:00..
        async with self.Session() as session:
            await self._insert_rain(session, code, times)
            report = await device_uptime.compute_outage_report(
                session,
                start=datetime(2026, 6, 20, 0, 0, 0),
                end=now,
                device_key=f"runoff_{code}",
                now=now,
            )
        rows = report["rows"]
        self.assertTrue(any(r["device_key"] == f"runoff_{code}" for r in rows))
        # 至少包含那段 4 小时的内部空档。
        internal = [r for r in rows if not r["ongoing"]]
        self.assertTrue(internal)
        self.assertGreaterEqual(max(r["duration_seconds"] for r in internal), 3 * 3600)

    async def test_empty_window_with_prior_data_counts_as_outage(self):
        code = "16132921"
        now = datetime(2026, 6, 21, 12, 0, 0)
        # 仅在很久以前有数据，最近一周窗口内完全没有数据 → 整窗口掉线。
        async with self.Session() as session:
            await self._insert_rain(session, code, [datetime(2026, 5, 1, 8, 0, 0)])
            report = await device_uptime.compute_outage_report(
                session,
                start=now - timedelta(days=7),
                end=now,
                device_key=f"runoff_{code}",
                now=now,
            )
        self.assertEqual(1, report["totals"]["range_count"])
        self.assertGreater(report["totals"]["range_duration_seconds"], 6 * 86400)

    async def test_never_online_device_has_no_outage(self):
        code = "16132922"
        now = datetime(2026, 6, 21, 12, 0, 0)
        async with self.Session() as session:  # 不插入任何数据
            report = await device_uptime.compute_outage_report(
                session,
                start=now - timedelta(days=7),
                end=now,
                device_key=f"runoff_{code}",
                now=now,
            )
        self.assertEqual(0, report["totals"]["range_count"])
        self.assertEqual([], report["rows"])

    async def test_current_status_uses_timestamp_freshness(self):
        now = datetime(2026, 6, 21, 12, 0, 0)
        async with self.Session() as session:
            # 16132920：刚上报（新鲜）→ online
            await self._insert_rain(session, "16132920", [now - timedelta(minutes=4)])
            # 16132921：1 小时前最后一条（陈旧，阈值30分钟）→ offline
            await self._insert_rain(session, "16132921", [now - timedelta(hours=1)])
            statuses = await device_uptime.compute_current_statuses(session, now=now)
        self.assertEqual("online", statuses["runoff_16132920"])
        self.assertEqual("offline", statuses["runoff_16132921"])
        # 从未上报的设备不纳入
        self.assertNotIn("runoff_16132922", statuses)

    async def test_status_snapshot_opens_then_closes_event(self):
        key = "runoff_16132920"
        t1 = datetime(2026, 6, 21, 10, 0, 0)
        t2 = datetime(2026, 6, 21, 10, 30, 0)
        async with self.Session() as session:
            await device_uptime.record_status_snapshot(session, {key: "offline"}, now=t1)
        async with self.Session() as session:
            events = (await session.execute(
                select(DeviceStatusEvent).where(DeviceStatusEvent.device_key == key)
            )).scalars().all()
            self.assertEqual(1, len(events))
            self.assertIsNone(events[0].ended_at)
        async with self.Session() as session:
            await device_uptime.record_status_snapshot(session, {key: "online"}, now=t2)
        async with self.Session() as session:
            events = (await session.execute(
                select(DeviceStatusEvent).where(DeviceStatusEvent.device_key == key)
            )).scalars().all()
            self.assertEqual(1, len(events))
            self.assertEqual(t2, events[0].ended_at)


if __name__ == "__main__":
    unittest.main()
