import asyncio
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

apscheduler_module = types.ModuleType("apscheduler")
apscheduler_schedulers = types.ModuleType("apscheduler.schedulers")
apscheduler_asyncio = types.ModuleType("apscheduler.schedulers.asyncio")
apscheduler_triggers = types.ModuleType("apscheduler.triggers")
apscheduler_interval = types.ModuleType("apscheduler.triggers.interval")


class _UnusedAsyncIOScheduler:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def add_job(self, *args, **kwargs):
        return None

    def start(self):
        return None

    def shutdown(self):
        return None


class _UnusedIntervalTrigger:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


apscheduler_asyncio.AsyncIOScheduler = _UnusedAsyncIOScheduler
apscheduler_interval.IntervalTrigger = _UnusedIntervalTrigger

sys.modules.setdefault("apscheduler", apscheduler_module)
sys.modules.setdefault("apscheduler.schedulers", apscheduler_schedulers)
sys.modules.setdefault("apscheduler.schedulers.asyncio", apscheduler_asyncio)
sys.modules.setdefault("apscheduler.triggers", apscheduler_triggers)
sys.modules.setdefault("apscheduler.triggers.interval", apscheduler_interval)

import main  # noqa: E402


class _FakeScheduler:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def shutdown(self):
        self.stopped = True


class MainSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "main-security-test.db"
        self.db_url = f"sqlite+aiosqlite:///{self.db_path.as_posix()}"
        self.scheduler = _FakeScheduler()
        self.run_collectors = AsyncMock()
        self.init_db = AsyncMock()
        self.patches = [
            patch.object(main.settings, "DATABASE_URL", self.db_url),
            patch.object(main.settings, "ACCESS_PASSWORD", "admin-pass"),
            patch.object(main.settings, "LEADER_ACCESS_PASSWORD", "leader-pass"),
            patch("main.init_db", new=self.init_db),
            patch("main._run_all_collectors", new=self.run_collectors),
            patch("main.setup_scheduler", return_value=self.scheduler),
        ]
        for active_patch in self.patches:
            active_patch.start()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def _login(self, password: str) -> dict:
        response = self.client.post("/api/auth/login", json={"password": password})
        self.assertEqual(200, response.status_code)
        return response.json()

    def test_leader_cannot_trigger_manual_collection(self):
        payload = self._login("leader-pass")
        self.assertEqual("leader", payload["role"])

        response = self.client.post("/api/collect/trigger")

        self.assertEqual(403, response.status_code)

    def test_leader_cannot_access_debug_settings(self):
        payload = self._login("leader-pass")
        self.assertEqual("leader", payload["role"])

        response = self.client.get("/api/debug/settings")

        self.assertEqual(403, response.status_code)


class LifespanBehaviorTests(unittest.TestCase):
    def test_lifespan_skips_initial_collection_when_disabled(self):
        scheduler = _FakeScheduler()
        run_collectors = AsyncMock()
        init_db = AsyncMock()

        async def run_lifespan():
            async with main.lifespan(main.app):
                return None

        with patch.object(main.settings, "RUN_COLLECTORS_ON_STARTUP", False):
            with patch("main.init_db", new=init_db):
                with patch("main._run_all_collectors", new=run_collectors):
                    with patch("main.setup_scheduler", return_value=scheduler):
                        asyncio.run(run_lifespan())

        init_db.assert_awaited_once()
        run_collectors.assert_not_awaited()
        self.assertTrue(scheduler.started)
        self.assertTrue(scheduler.stopped)
