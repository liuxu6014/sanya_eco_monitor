import inspect
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers import report  # noqa: E402


class ReportGenerationFlowTests(unittest.TestCase):
    def test_background_report_generation_reopens_database_sessions(self):
        source = inspect.getsource(report._build_and_store_report)
        self.assertGreaterEqual(source.count("async with AsyncSessionLocal() as db"), 3)


if __name__ == "__main__":
    unittest.main()
