import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.chart_service import generate_all_charts  # noqa: E402
from services.report_figures import build_figure_manifest  # noqa: E402
from services.report_service import build_history_comparison_summary  # noqa: E402


class HistoryComparisonOutputTests(unittest.TestCase):
    def test_build_history_comparison_summary_returns_module_deltas(self):
        current_period = {"start": "2026-03-25", "end": "2026-04-23"}
        previous_period = {"start": "2026-02-23", "end": "2026-03-24"}
        current = {
            "insect": {"total_count": 73},
            "spore": {"total_count": 22},
            "rain": {"total_rainfall": 188.5},
            "runoff": {"total_runoff": 24.6},
            "water_quality": {
                "avg_nh3_n": 0.13,
                "avg_tp": 0.02,
                "avg_permanganate": 1.8,
                "avg_tn": 0.57,
            },
        }
        previous = {
            "insect": {"total_count": 58},
            "spore": {"total_count": 17},
            "rain": {"total_rainfall": 132.0},
            "runoff": {"total_runoff": 18.4},
            "water_quality": {
                "avg_nh3_n": 0.21,
                "avg_tp": 0.03,
                "avg_permanganate": 2.1,
                "avg_tn": 0.63,
            },
        }

        history = build_history_comparison_summary(
            current_period=current_period,
            previous_period=previous_period,
            current=current,
            previous=previous,
        )

        self.assertEqual(previous_period, history["previous_period"])
        self.assertEqual(25.9, history["modules"]["insect"]["change_rate"])
        self.assertEqual("上升", history["modules"]["rain"]["trend"])
        self.assertEqual("下降", history["water_quality"]["metrics"][0]["trend"])

    def test_generate_all_charts_and_manifest_include_history_comparison_figures(self):
        summary = {
            "insect": {"daily": [{"date": "2026-04-01", "count": 12}], "top_species": [["金龟子", 32]]},
            "spore": {"daily": [{"date": "2026-04-01", "count": 3}]},
            "rain": {"daily": [{"date": "2026-04-01", "rainfall": 18.5}], "total_rainfall": 188.5},
            "runoff": {
                "by_device": {
                    "16132922": {"name": "次生林监测点", "total_runoff": 24.6},
                    "16132921": {"name": "橡胶林监测点", "total_runoff": 12.2},
                }
            },
            "water_quality": {
                "avg_nh3_n": 0.13,
                "avg_tp": 0.02,
                "avg_permanganate": 1.8,
                "avg_tn": 0.57,
            },
            "history_comparison": {
                "modules": {
                    "insect": {"label": "虫情测报", "unit": "%", "change_rate": 25.9},
                    "spore": {"label": "孢子监测", "unit": "%", "change_rate": 29.4},
                    "rain": {"label": "雨量监测", "unit": "%", "change_rate": 42.8},
                    "runoff": {"label": "地表径流监测", "unit": "%", "change_rate": 33.7},
                },
                "water_quality": {
                    "metrics": [
                        {"label": "氨氮", "current_value": 0.13, "previous_value": 0.21},
                        {"label": "总磷", "current_value": 0.02, "previous_value": 0.03},
                        {"label": "高锰酸盐指数", "current_value": 1.8, "previous_value": 2.1},
                        {"label": "总氮", "current_value": 0.57, "previous_value": 0.63},
                    ]
                },
            },
        }

        charts = generate_all_charts(summary)

        self.assertTrue(charts["核心指标历史对比"])
        self.assertTrue(charts["水质历史对比"])

        manifest = build_figure_manifest(summary, charts, {})
        captions = [item["caption"] for item in manifest]
        self.assertIn("本期与上一等长周期核心监测指标变化率", captions)
        self.assertIn("水质关键指标本期与上一周期均值对比", captions)


if __name__ == "__main__":
    unittest.main()
