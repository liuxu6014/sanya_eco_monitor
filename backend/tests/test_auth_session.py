import sys
import sqlite3
import unittest
from contextlib import closing
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from fastapi import Response


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auth  # noqa: E402


class AuthSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "auth-session-test.db"
        self.db_url = f"sqlite+aiosqlite:///{self.db_path.as_posix()}"
        self.database_patch = patch.object(auth.settings, "DATABASE_URL", self.db_url)
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_set_auth_cookie_creates_distinct_valid_sessions(self):
        response_a = Response()
        response_b = Response()

        auth.set_auth_cookie(response_a, role="admin")
        auth.set_auth_cookie(response_b, role="admin")

        cookie_a = response_a.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        cookie_b = response_b.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]

        self.assertNotEqual(cookie_a, cookie_b)
        self.assertTrue(auth.is_valid_auth_cookie(cookie_a))
        self.assertTrue(auth.is_admin_auth_cookie(cookie_a))
        self.assertTrue(auth.is_valid_auth_cookie(cookie_b))
        self.assertEqual("admin", auth.auth_role_from_cookie(cookie_b))

    def test_set_auth_cookie_persists_session_to_database(self):
        response = Response()

        auth.set_auth_cookie(response, role="admin")

        cookie_value = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        self.assertTrue(self.db_path.exists())
        self.assertTrue(auth.is_valid_auth_cookie(cookie_value))

        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("SELECT role FROM auth_sessions").fetchall()

        self.assertEqual([("admin",)], rows)

    def test_clear_auth_cookie_revokes_session(self):
        response = Response()
        auth.set_auth_cookie(response, role="leader")
        cookie_value = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]

        self.assertTrue(auth.is_valid_auth_cookie(cookie_value))
        auth.clear_auth_cookie(Response(), cookie_value=cookie_value)

        self.assertFalse(auth.is_valid_auth_cookie(cookie_value))
        self.assertIsNone(auth.auth_role_from_cookie(cookie_value))

        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("SELECT role FROM auth_sessions").fetchall()

        self.assertEqual([], rows)

    def test_secure_cookie_follows_setting(self):
        with patch.object(auth.settings, "AUTH_COOKIE_SECURE", True):
            response = Response()
            auth.set_auth_cookie(response, role="admin")

        self.assertIn("Secure", response.headers["set-cookie"])

    def test_validating_cookie_does_not_require_a_write_lock(self):
        response = Response()
        auth.set_auth_cookie(response, role="admin")
        cookie_value = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]

        locker = sqlite3.connect(self.db_path, timeout=0.1, isolation_level=None)
        try:
            locker.execute("BEGIN IMMEDIATE")
            self.assertTrue(auth.is_valid_auth_cookie(cookie_value))
        finally:
            locker.rollback()
            locker.close()


if __name__ == "__main__":
    unittest.main()
