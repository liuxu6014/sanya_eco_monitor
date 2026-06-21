import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.summary import RUNOFF_DEVICES  # noqa: E402
from services.guideline_metrics import RUNOFF_DEVICE_NAMES  # noqa: E402


class RunoffDeviceMappingTests(unittest.TestCase):
    def test_guideline_runoff_device_mapping_matches_field_inventory(self):
        self.assertEqual(
            {
                "16132920": "橡胶林径流点 1",
                "16132921": "次生林径流点",
                "16132922": "芒果林径流点 1",
                "16132923": "槟榔林径流点",
                "16132924": "橡胶林径流点 2",
                "16132925": "芒果林径流点 2",
            },
            RUNOFF_DEVICE_NAMES,
        )

    def test_summary_runoff_device_mapping_matches_field_inventory(self):
        self.assertEqual(
            [
                ("16132920", "橡胶林径流监测系统1号"),
                ("16132921", "次生林径流监测系统"),
                ("16132922", "芒果林径流监测系统1号"),
                ("16132923", "槟榔林径流监测系统"),
                ("16132924", "橡胶林径流监测系统2号"),
                ("16132925", "芒果林径流监测系统2号"),
            ],
            RUNOFF_DEVICES,
        )


if __name__ == "__main__":
    unittest.main()
